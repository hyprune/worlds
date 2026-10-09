// SPDX-License-Identifier: MIT
// From-cell potentially visible sets for derived world visibility (tools/derive-visibility.py).
//
// Sampled precomputed visibility, as in engine "precomputed visibility volumes":
// a unit (glTF mesh node) is visible from a cell if any segment from a cell eye
// sample to a sample point on the unit's surface, or any forward ray from a cell
// eye sample, first hits that unit. Occluders are opaque triangles; single-sided
// back faces never occlude (the renderer culls them). Textbook median-split BVH and
// Moller-Trumbore intersection; no third-party code. Batch work: run on the bake
// host (AGENTS.md rule 3), e.g. `pvs request.bin result.bin $(nproc)`.
//
// request.bin (little endian):
//   "HPVS1\0\0\0", u32 triangles, u32 units, u32 cells, u32 forwardRays
//   triangles x { f32 a[3], b[3], c[3]; i32 unit (-1: none); u8 flags (1 occluder, 2 double-sided) }
//   units x { u32 n; f32 points[n][3] }
//   cells x { u32 n; f32 eyes[n][3] }
// result.bin: "HPVR1\0\0\0", u32 cells, u32 units, then cells x units bytes:
//   0 hidden, 1 visible by forward ray, 2 visible by targeted segment.
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <numeric>
#include <random>
#include <stdexcept>
#include <thread>
#include <vector>

struct V {
    float x, y, z;
};
static V operator-(V a, V b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
static V operator+(V a, V b) { return {a.x + b.x, a.y + b.y, a.z + b.z}; }
static V operator*(V a, float s) { return {a.x * s, a.y * s, a.z * s}; }
static float dot(V a, V b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
static V cross(V a, V b) { return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x}; }
static float axis(V v, int a) { return a == 0 ? v.x : a == 1 ? v.y : v.z; }

struct Tri {
    V a, b, c, n;
    int unit;
    uint8_t flags;
};
struct Box {
    V lo{INFINITY, INFINITY, INFINITY}, hi{-INFINITY, -INFINITY, -INFINITY};
    void add(V p) {
        lo = {std::min(lo.x, p.x), std::min(lo.y, p.y), std::min(lo.z, p.z)};
        hi = {std::max(hi.x, p.x), std::max(hi.y, p.y), std::max(hi.z, p.z)};
    }
};
struct Node {
    Box box;
    uint32_t left = 0, right = 0, begin = 0, end = 0;
};

class Bvh {
  public:
    explicit Bvh(std::vector<Tri> &t) : tris(t) {
        order.resize(t.size());
        std::iota(order.begin(), order.end(), 0u);
        nodes.reserve(t.size() / 2 + 1);
        if (!t.empty())
            build(0, t.size());
    }
    // Nearest relevant hit in (0, tMax]: triangles that occlude, or belong to `unit`.
    // Returns the unit of the hit triangle, -2 for no hit.
    int first(V o, V d, float tMax, int unit) const {
        V inv{1 / d.x, 1 / d.y, 1 / d.z};
        float best = tMax;
        int hitUnit = -2;
        uint32_t stack[128];
        int top = 0;
        stack[top++] = 0;
        while (top) {
            const Node &n = nodes[stack[--top]];
            if (!slab(n.box, o, inv, best))
                continue;
            if (n.left) {
                stack[top++] = n.right;
                stack[top++] = n.left;
                continue;
            }
            for (uint32_t i = n.begin; i < n.end; ++i) {
                const Tri &t = tris[order[i]];
                if (!(t.flags & 1) && t.unit != unit)
                    continue;
                if (!(t.flags & 2) && dot(t.n, d) > 0)
                    continue; // culled back face
                float h = intersect(t, o, d);
                if (h > 1e-5f && h < best) {
                    best = h;
                    hitUnit = t.unit;
                }
            }
        }
        return hitUnit;
    }

  private:
    std::vector<Tri> &tris;
    std::vector<uint32_t> order;
    std::vector<Node> nodes;
    uint32_t build(uint32_t begin, uint32_t end) {
        uint32_t id = nodes.size();
        nodes.emplace_back();
        Node n;
        n.begin = begin;
        n.end = end;
        for (uint32_t i = begin; i < end; ++i) {
            auto &t = tris[order[i]];
            n.box.add(t.a), n.box.add(t.b), n.box.add(t.c);
        }
        if (end - begin > 4) {
            V e = n.box.hi - n.box.lo;
            int a = e.y > e.x ? 1 : 0;
            if (e.z > axis(e, a))
                a = 2;
            uint32_t mid = begin + (end - begin) / 2;
            std::nth_element(order.begin() + begin, order.begin() + mid, order.begin() + end, [&](uint32_t p, uint32_t q) {
                auto &s = tris[p], &u = tris[q];
                return axis(s.a + s.b + s.c, a) < axis(u.a + u.b + u.c, a);
            });
            n.left = build(begin, mid);
            n.right = build(mid, end);
        }
        nodes[id] = n;
        return id;
    }
    static bool slab(const Box &b, V o, V inv, float tMax) {
        float t0 = 0, t1 = tMax;
        for (int a = 0; a < 3; ++a) {
            float lo = (axis(b.lo, a) - axis(o, a)) * axis(inv, a), hi = (axis(b.hi, a) - axis(o, a)) * axis(inv, a);
            if (lo > hi)
                std::swap(lo, hi);
            t0 = std::max(t0, lo);
            t1 = std::min(t1, hi * 1.000001f);
            if (t0 > t1)
                return false;
        }
        return true;
    }
    static float intersect(const Tri &t, V o, V d) {
        V e1 = t.b - t.a, e2 = t.c - t.a, p = cross(d, e2);
        float det = dot(e1, p);
        if (std::fabs(det) < 1e-12f)
            return -1;
        float inv = 1 / det;
        V s = o - t.a;
        float u = dot(s, p) * inv;
        if (u < 0 || u > 1)
            return -1;
        V q = cross(s, e1);
        float v = dot(d, q) * inv;
        if (v < 0 || u + v > 1)
            return -1;
        return dot(e2, q) * inv;
    }
};

template <class T> static T get(std::ifstream &in) {
    T v;
    in.read(reinterpret_cast<char *>(&v), sizeof v);
    if (!in)
        throw std::runtime_error("truncated request");
    return v;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        std::fprintf(stderr, "usage: pvs request.bin result.bin [threads]\n");
        return 2;
    }
    std::ifstream in(argv[1], std::ios::binary);
    char magic[8];
    in.read(magic, 8);
    if (std::memcmp(magic, "HPVS1\0\0\0", 8))
        throw std::runtime_error("bad request magic");
    auto nTri = get<uint32_t>(in), nUnits = get<uint32_t>(in), nCells = get<uint32_t>(in), forward = get<uint32_t>(in);
    std::vector<Tri> tris(nTri);
    for (auto &t : tris) {
        float f[9];
        in.read(reinterpret_cast<char *>(f), sizeof f);
        t.a = {f[0], f[1], f[2]}, t.b = {f[3], f[4], f[5]}, t.c = {f[6], f[7], f[8]};
        t.unit = get<int32_t>(in);
        t.flags = get<uint8_t>(in);
        t.n = cross(t.b - t.a, t.c - t.a);
    }
    auto points = [&] {
        std::vector<V> p(get<uint32_t>(in));
        in.read(reinterpret_cast<char *>(p.data()), p.size() * sizeof(V));
        return p;
    };
    std::vector<std::vector<V>> targets(nUnits), cells(nCells);
    for (auto &u : targets)
        u = points();
    for (auto &c : cells)
        c = points();
    if (!in)
        throw std::runtime_error("truncated request");
    Bvh bvh(tris);

    // Uniform forward directions (Fibonacci sphere), shared by every eye sample.
    std::vector<V> dirs(forward);
    for (uint32_t i = 0; i < forward; ++i) {
        float y = 1 - 2 * (i + .5f) / forward, r = std::sqrt(std::max(0.f, 1 - y * y)), phi = i * 2.39996323f;
        dirs[i] = {r * std::cos(phi), y, r * std::sin(phi)};
    }
    std::vector<uint8_t> result(size_t(nCells) * nUnits, 0);
    std::atomic<uint32_t> next{0};
    std::atomic<uint64_t> rays{0};
    int threads = argc > 3 ? std::atoi(argv[3]) : std::thread::hardware_concurrency();
    std::vector<std::thread> pool;
    for (int w = 0; w < std::max(1, threads); ++w)
        pool.emplace_back([&] {
            uint64_t local = 0;
            for (uint32_t c; (c = next++) < nCells;) {
                uint8_t *row = &result[size_t(c) * nUnits];
                const float far = 1e5f;
                for (V eye : cells[c])
                    for (V d : dirs) {
                        ++local;
                        int u = bvh.first(eye, d, far, -1);
                        if (u >= 0)
                            row[u] = std::max<uint8_t>(row[u], 1);
                    }
                std::mt19937 rng(c * 2654435761u + 7);
                for (uint32_t u = 0; u < nUnits; ++u) {
                    if (row[u] || cells[c].empty() || targets[u].empty())
                        continue;
                    // Interleave eye samples and surface points; early out on the first hit.
                    size_t pairs = cells[c].size() * targets[u].size();
                    size_t stride = 1 + rng() % std::max<size_t>(1, pairs - 1);
                    while (std::gcd(stride, pairs) != 1)
                        ++stride;
                    size_t k = rng() % pairs;
                    for (size_t i = 0; i < pairs; ++i, k = (k + stride) % pairs) {
                        V eye = cells[c][k % cells[c].size()], target = targets[u][k / cells[c].size()];
                        ++local;
                        if (bvh.first(eye, target - eye, 1.001f, u) == int(u)) {
                            row[u] = 2;
                            break;
                        }
                    }
                }
            }
            rays += local;
        });
    for (auto &t : pool)
        t.join();
    std::ofstream out(argv[2], std::ios::binary);
    out.write("HPVR1\0\0\0", 8);
    out.write(reinterpret_cast<const char *>(&nCells), 4);
    out.write(reinterpret_cast<const char *>(&nUnits), 4);
    out.write(reinterpret_cast<const char *>(result.data()), result.size());
    std::printf("{\"triangles\":%u,\"units\":%u,\"cells\":%u,\"forwardRays\":%u,\"rays\":%llu}\n", nTri, nUnits, nCells,
                forward, (unsigned long long)rays.load());
    return 0;
}

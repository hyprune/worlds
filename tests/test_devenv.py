#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Developer settings: environment over ~/.config/hyprune/dev.env; the bake host is never implicit."""
import contextlib, io, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import devenv  # noqa: E402


class DevEnv(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        env = {k: v for k, v in os.environ.items() if k not in devenv.KEYS}
        env.update(XDG_CONFIG_HOME=str(self.tmp / 'config'), XDG_STATE_HOME=str(self.tmp / 'state'))
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        devenv._warned.clear()

    def write(self, text):
        (self.tmp / 'config/hyprune').mkdir(parents=True, exist_ok=True)
        (self.tmp / 'config/hyprune/dev.env').write_text(text)

    def bake(self, **env):
        script = 'source tools/bake-host.sh; echo "$HOST $BAKE_LOCAL $(host_path work)"'
        return subprocess.run(['bash', '-c', script], cwd=ROOT, capture_output=True, text=True,
                              env={**os.environ, 'ROOT': str(ROOT), **env})

    def test_environment_wins_over_file(self):
        self.write('HYPRUNE_VIDEO_DIR=/from-file\n')
        self.assertEqual(devenv.get('HYPRUNE_VIDEO_DIR'), '/from-file')
        os.environ['HYPRUNE_VIDEO_DIR'] = str(self.tmp / 'env')
        self.assertEqual(devenv.video_dir(), self.tmp / 'env')

    def test_unconfigured_video_dir_warns_with_its_fallback(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            path = devenv.video_dir()
        self.assertEqual(path, self.tmp / 'state/hyprune/videos')
        self.assertIn('HYPRUNE_VIDEO_DIR is not set', err.getvalue())
        self.assertIn(str(path), err.getvalue())

    def test_bake_host_is_required(self):
        r = self.bake()
        self.assertEqual(r.returncode, 2)
        self.assertIn('Set HYPRUNE_BAKE_HOST', r.stderr)
        self.assertEqual(self.bake(HYPRUNE_BAKE_HOST='localhost').returncode, 2)

    def test_local_bake_host_from_file(self):
        self.write("HYPRUNE_BAKE_HOST='local'\n")
        r = self.bake()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split(), ['local', '1', str(Path.home() / 'work')])


if __name__ == '__main__':
    unittest.main()

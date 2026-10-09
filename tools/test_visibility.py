#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Regression cases for dangerous visibility authoring mistakes."""
import copy,importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('audit',Path(__file__).with_name('check-visibility.py'));audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
class VisibilityContract(unittest.TestCase):
 def setUp(self):
  self.areas=[{'id':'court','bounds':{'min':[0,0,0],'max':[1,1,1]},'nodes':[0],'visibleFrom':[]},{'id':'entry','bounds':{'min':[1,0,0],'max':[2,1,1]},'nodes':[1],'visibleFrom':['court']},{'id':'vault','bounds':{'min':[2,0,0],'max':[3,1,1]},'nodes':[2],'visibleFrom':['entry']}]
 def test_directed_not_transitive(self):
  self.assertEqual(audit.visible_areas(self.areas,[.5,.5,.5]),{'court','entry'})
  self.assertEqual(audit.visible_areas(self.areas,[2.5,.5,.5]),{'vault'})
 def test_inclusive_overlap_and_outside(self):
  self.assertEqual(audit.visible_areas(self.areas,[1,.5,.5]),{'court','entry','vault'})
  self.assertEqual(audit.visible_areas(self.areas,[-1,.5,.5]),{'court','entry','vault'})
 def test_nested_ownership_rejected(self):
  scene={'nodes':[{'children':[1]},{},{}]}
  with self.assertRaisesRegex(AssertionError,'overlapping'):audit.validate({'visibility':{'areas':self.areas}},scene)
 def test_unknown_source_rejected(self):
  self.areas[0]['visibleFrom']=['typo']
  with self.assertRaisesRegex(AssertionError,'unknown directed'):audit.validate({'visibility':{'areas':self.areas}},{'nodes':[{}, {}, {}]})
if __name__=='__main__':unittest.main()

"""Integration regression for Debian setuptools on a vanilla interpreter."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class DebianInstallLayout(unittest.TestCase):
    def paths(self, **options):
        driver = '''
import json, sys
from setuptools import Distribution
from setuptools.command.install import install
command = install(Distribution())
for key, value in json.loads(sys.argv[1]).items():
    setattr(command, key, value)
command.ensure_finalized()
print(json.dumps({key: getattr(command, key) for key in
    ('install_lib', 'install_scripts', 'install_data', 'prefix_option')}))
'''
        output = subprocess.check_output([sys.executable, '-c', driver, json.dumps(options)], text=True)
        return json.loads(output)

    def test_deb_layout_and_root(self):
        paths = self.paths(install_layout='deb', root='/staging')
        self.assertEqual(paths['install_lib'], '/staging/usr/lib/python3/dist-packages/')
        self.assertEqual(paths['install_scripts'], '/staging/usr/bin')
        self.assertEqual(paths['install_data'], '/staging/usr')

    def test_explicit_prefix_retained(self):
        paths = self.paths(install_layout='deb', prefix='/custom', root='/staging')
        self.assertEqual(paths['install_lib'], '/staging/custom/lib/python3/dist-packages/')
        self.assertEqual(paths['install_scripts'], '/staging/custom/bin')

    def test_vanilla_layout_retained(self):
        paths = self.paths(prefix='/custom', root='/staging')
        self.assertIn('/staging/custom/', paths['install_lib'])
        self.assertIn('site-packages', paths['install_lib'])

    def test_unknown_layout_rejected(self):
        for layout in ('unknown', 'unix'):
            with self.subTest(layout=layout), self.assertRaises(subprocess.CalledProcessError):
                self.paths(install_layout=layout)

    def test_actual_install(self):
        with tempfile.TemporaryDirectory(prefix='setuptools-layout-') as temporary:
            root = Path(temporary)
            (root / 'setup.py').write_text('from setuptools import setup\nsetup(name="layout-probe", version="1.0", py_modules=["probe"])\n')
            (root / 'probe.py').write_text('VALUE = 42\n')
            subprocess.run([sys.executable, 'setup.py', 'install', '--install-layout=deb', '--root=' + str(root / 'stage')],
                           cwd=root, check=True, stdout=subprocess.DEVNULL)
            directory = root / 'stage/usr/lib/python3/dist-packages'
            self.assertEqual((directory / 'probe.py').read_text(), 'VALUE = 42\n')
            self.assertTrue((directory / 'layout_probe-1.0.egg-info').is_dir(), list(directory.iterdir()))
            self.assertFalse((root / 'stage/opt').exists())


if __name__ == '__main__':
    unittest.main()

import zipimport
import py

import os
import py_compile
import shutil
import time
import zipfile
from pypy.conftest import gettestobjspace

example_code = 'attr = None'

created_paths = set(['_top_level',
                     os.path.join('_pkg', '__init__'),
                     os.path.join('_pkg', 'submodule'),
                     os.path.join('_pkg', '_subpkg', '__init__'),
                     os.path.join('_pkg', '_subpkg', 'submodule')
                    ])

py.test.skip("Completely broken")

def temp_zipfile(source=True, bytecode=True):
    """Create a temporary zip file for testing.

    Clears zipimport._zip_directory_cache.

    """
    zipimport._zip_directory_cache = {}
    zip_path = test_support.TESTFN + '.zip'
    bytecode_suffix = 'c' if __debug__ else 'o'
    zip_file = zipfile.ZipFile(zip_path, 'w')
    try:
        for path in created_paths:
            if os.sep in path:
                directory = os.path.split(path)[0]
                if not os.path.exists(directory):
                    os.makedirs(directory)
            code_path = path + '.py'
            try:
                temp_file = open(code_path, 'w')
                temp_file.write(example_code)
            finally:
                temp_file.close()
            if source:
                zip_file.write(code_path)
            if bytecode:
                py_compile.compile(code_path, doraise=True)
                zip_file.write(code_path + bytecode_suffix)
        zip_file.close()
        yield os.path.abspath(zip_path)
    finally:
        zip_file.close()
        for path in created_paths:
            if os.sep in path:
                directory = os.path.split(path)[0]
                if os.path.exists(directory):
                    shutil.rmtree(directory)
            else:
                for suffix in ('.py', '.py' + bytecode_suffix):
                    test_support.unlink(path + suffix)
        test_support.unlink(zip_path)


class AppTestZipImport:
    def setup_class(cls):
        space = gettestobjspace(usemodules=['zipimport', 'zlib', 'rctime'])
        cls.space = space

    def test_inheritance(self):
        # Should inherit from ImportError.
        import zipimport
        assert issubclass(zipimport.ZipImportError, ImportError)

    def test_nonzip(self):
        # ZipImportError should be raised if a non-zip file is specified.
        try:
            test_file = open(test_support.TESTFN, 'w')
            test_file.write("# Test file for zipimport.")
            try:
                raises(zipimport.ZipImportError,
                        zipimport.zipimporter, test_support.TESTFN)
            finally:
                test_support.unlink(test_support.TESTFN)
        finally:
            test_file.close()

    def test_root(self):
        raises(zipimport.ZipImportError, zipimport.zipimporter,
                            os.sep)


    def test_direct_path(self):
        # A zipfile should return an instance of zipimporter.
        try:
            zip_path = temp_zipfile()
            zip_importer = zipimport.zipimporter(zip_path)
            assert isinstance(zip_importer, zipimport.zipimporter)
            assert zip_importer.archive == zip_path
            assert zip_importer.prefix == ''
            assert zip_path in zipimport._zip_directory_cache
        finally:
            zip_path.close()

    def test_pkg_path(self):
        # Thanks to __path__, need to be able to work off of a path with a zip
        # file at the front and a path for the rest.
        try:
            zip_path = temp_zipfile()
            prefix = '_pkg'
            path = os.path.join(zip_path, prefix)
            zip_importer = zipimport.zipimporter(path)
            assert isinstance(zip_importer, zipimport.zipimporter)
            assert zip_importer.archive == zip_path
            assert zip_importer.prefix == prefix
            assert zip_path in zipimport._zip_directory_cache
        finally:
            zip_path.close()

    def test_zip_directory_cache(self):
        # Test that _zip_directory_cache is set properly.
        # Using a package entry to test using a hard example.
        try:
            zip_path = temp_zipfile(bytecode=False)
            importer = zipimport.zipimporter(os.path.join(zip_path, '_pkg'))
            assert zip_path in zipimport._zip_directory_cache
            file_set = set(zipimport._zip_directory_cache[zip_path].iterkeys())
            compare_set = set(path + '.py' for path in created_paths)
            assert file_set == compare_set
        finally:
            zip_path.close()

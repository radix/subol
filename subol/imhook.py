import os, sys
import ihooks, imp

from subol import sub2py

import __builtin__

from imp import C_EXTENSION, PY_SOURCE, PY_COMPILED
from imp import C_BUILTIN, PY_FROZEN, PKG_DIRECTORY
BUILTIN_MODULE = C_BUILTIN
FROZEN_MODULE = PY_FROZEN


class GoodHooks(ihooks.Hooks):
    def __init__(self, id, extension, mode='r'):
        self.id = id
        self.extension = extension
        self.mode = mode

    def get_suffixes(self):
        return imp.get_suffixes() + [(self.extension, self.mode, self.id)]


class Nothing: pass

class GoodModuleLoader(ihooks.ModuleLoader):
    def __init__(self, extension, executor):
        self.extension = extension
        self.executor = executor
        self.id = Nothing()
        self.hooks = GoodHooks(self.id, extension)

    def load_module(self, name, stuff):
        #raped'n'pasted from ihooks.FancyModuleLoader.load_module
        file, filename, (suff, mode, type) = stuff
        realfilename = filename
        path = None

        if type == PKG_DIRECTORY:
            initstuff = self.find_module_in_dir("__init__", filename, 0)
            if not initstuff:
                raise ImportError, "No __init__ module in package %s" % name
            initfile, initfilename, initinfo = initstuff
            initsuff, initmode, inittype = initinfo
            if inittype not in (PY_COMPILED, PY_SOURCE, self.id): # <-- this here's different
                if initfile: initfile.close()
                raise ImportError, \
                    "Bad type (%s) for __init__ module in package %s" % (
                    `inittype`, name)
            path = [filename]
            file = initfile
            realfilename = initfilename
            type = inittype

        if type == FROZEN_MODULE:
            code = self.hooks.get_frozen_object(name)
        elif type == PY_COMPILED:
            import marshal
            file.seek(8)
            code = marshal.load(file)
        elif type == PY_SOURCE:
            data = file.read()
            code = compile(data, realfilename, 'exec')
        elif type == self.id: # <-- this here's different
            specialcode = file.read()
        else:
            return ihooks.ModuleLoader.load_module(self, name, stuff)

        m = self.hooks.add_module(name)
        if path:
            m.__path__ = path
        m.__file__ = filename

        if type == self.id:
            self.executor(specialcode, m.__dict__, filename)
        else:
            exec code in m.__dict__

        return m


class GoodImporter(ihooks.ModuleImporter):

    def import_module(self, name, globals={}, locals={}, fromlist=[], level=-1):
        ## This method deserves some explanation.

        ## First of all, this is a performance hack. Using ihooks'
        ## implementation of import is a huge performance hit.  So
        ## we're going to try to use the built-in __import__ in the
        ## common case, and when it doesn't give us what we want,
        ## we'll fall back to our hooked version.
        try:
            m = self.save_import_module(name, globals, locals, fromlist)

            ## If someone's trying to import *, we want to make sure
            ## that they really got all of the modules listed in a
            ## package's __all__. If __import__ hasn't got all of
            ## them, perhaps one of them is a non-Python module; fall
            ## back.
            
            if fromlist and '*' in fromlist:
                all = getattr(m, '__all__', [])
                for x in all:
                    if not hasattr(m, x):
                        raise ImportError

            if not fromlist or '*' in fromlist:
                return m

            ## So, say we've already got, say, subol.test imported,
            ## but we're trying to import a `suboltest.sub' file
            ## that's living in it. `from subol.test import suboltest'
            ## will call __import__(name, g, l, ['suboltest']), and
            ## __import__ just happens to ignore any `from' items that
            ## don't exist. So we're going to make sure that
            ## __import__ did indeed get all of the items in the
            ## fromlist; if it didn't, then someone may be trying to
            ## import a subol file, so we'll fall back.

            for x in fromlist:
                if not hasattr(m, x):
                    raise ImportError

        except ImportError:
            m = ihooks.ModuleImporter.import_module(self, name, globals, locals, fromlist)
        if not m:
            raise ImportError
        return m

##    def import_it(self, partname, fqname, parent, force_load=0):
##        import pdb; pdb.set_trace()
##        print "import_it", repr(partname), repr(fqname), repr(parent), repr(force_load)
##        if not partname:
##            raise ValueError, "Empty module name"
##        if not force_load:
##            try:
##                m = self.modules[fqname]
##                if m:
##                    return m
##                else:
##                    print "cleaning up", fqname
##                    del self.modules[fqname]
##            except KeyError:
##                pass
##        try:
##            path = parent and parent.__path__
##            print "path", path
##        except AttributeError:
##            print "attrerror..."
##            return None
##        stuff = self.loader.find_module(partname, path)
##        print "stuff", stuff
##        if not stuff:
##            return None
##        m = self.loader.load_module(fqname, stuff)
##        print "M!!!", m
##        if parent:
##            setattr(parent, partname, m)
##        return m

installed = False

def installImportHook():
    global installed
    mi = GoodImporter(loader=GoodModuleLoader('.sub', lambda c, n, filename: sub2py.run(c,n,'exec', filename)))
    mi.install()
    installed = True


#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Patching rope:

Copyright © 2011 Pierre Raybaut
Licensed under the terms of the MIT License
(see spyderlib/__init__.py for details)

[1] For better performances, see this thread:
http://groups.google.com/group/rope-dev/browse_thread/thread/57de5731f202537a

[2] To avoid considering folders without __init__.py as Python packages, thus
avoiding side effects as non-working introspection features on a Python module
or package when a folder in current directory has the same name.
See this thread:
http://groups.google.com/group/rope-dev/browse_thread/thread/924c4b5a6268e618

[3] To avoid rope adding a 2 spaces indent to every docstring it gets, because
it breaks the work of Sphinx on the Object Inspector.
"""

import inspect

def apply():
    """Monkey patching rope
    
    See [1], [2] and [3] in module docstring."""
    import rope
    if rope.VERSION not in ('0.9.4', '0.9.3', '0.9.2'):
        raise ImportError, "rope %s can't be patched" % rope.VERSION

    # Patching pycore.PyCore...
    from rope.base import pycore
    class PatchedPyCore(pycore.PyCore):
        # [1] ...so that forced builtin modules (i.e. modules that were 
        # declared as 'extension_modules' in rope preferences) will be indeed
        # recognized as builtins by rope, as expected
        # 
        # This patch is included in rope 0.9.4+ but applying it anyway is ok
        def get_module(self, name, folder=None):
            """Returns a `PyObject` if the module was found."""
            # check if this is a builtin module
            pymod = self._builtin_module(name)
            if pymod is not None:
                return pymod
            module = self.find_module(name, folder)
            if module is None:
                raise pycore.ModuleNotFoundError(
                                            'Module %s not found' % name)
            return self.resource_to_pyobject(module)
        # [2] ...to avoid considering folders without __init__.py as Python
        # packages
        def _find_module_in_folder(self, folder, modname):
            module = folder
            packages = modname.split('.')
            for pkg in packages[:-1]:
                if  module.is_folder() and module.has_child(pkg):
                    module = module.get_child(pkg)
                else:
                    return None
            if module.is_folder():
                if module.has_child(packages[-1]) and \
                   module.get_child(packages[-1]).is_folder() and \
                   module.get_child(packages[-1]).has_child('__init__.py'):
                    return module.get_child(packages[-1])
                elif module.has_child(packages[-1] + '.py') and \
                     not module.get_child(packages[-1] + '.py').is_folder():
                    return module.get_child(packages[-1] + '.py')
    pycore.PyCore = PatchedPyCore
    
    # [1] Patching BuiltinFunction for the calltip/doc functions to be 
    # able to retrieve the function signatures with forced builtins
    from rope.base import builtins, pyobjects
    class PatchedBuiltinFunction(builtins.BuiltinFunction):
        def __init__(self, returned=None, function=None, builtin=None,
                     argnames=[], parent=None):
            builtins._BuiltinElement.__init__(self, builtin, parent)
            pyobjects.AbstractFunction.__init__(self)
            self.argnames = argnames
            if not argnames and builtin:
                self.argnames = getargs(self.builtin)
            if self.argnames is None:
                self.argnames = []
            self.returned = returned
            self.function = function
    builtins.BuiltinFunction = PatchedBuiltinFunction

    # [1] Patching BuiltinName for the go to definition feature to simply work 
    # with forced builtins
    from rope.base import libutils
    import inspect
    class PatchedBuiltinName(builtins.BuiltinName):
        def _pycore(self):
            p = self.pyobject
            while p.parent is not None:
                p = p.parent
            if isinstance(p, builtins.BuiltinModule) and p.pycore is not None:
                return p.pycore
        def get_definition_location(self):
            if not inspect.isbuiltin(self.pyobject):
                _lines, lineno = inspect.getsourcelines(self.pyobject.builtin)
                path = inspect.getfile(self.pyobject.builtin)
                pycore = self._pycore()
                if pycore and pycore.project:
                    resource = libutils.path_to_resource(pycore.project, path)
                    module = pyobjects.PyModule(pycore, None, resource)
                    return (module, lineno)
            return (None, None)
    builtins.BuiltinName = PatchedBuiltinName
    
    # [3] Patching PyDocExtractor so that _get_class_docstring and
    # _get_single_function_docstring don't add a 2 spaces indent to
    # every docstring. The only value that we are modifying is the indent
    # keyword, from 2 to 0.
    from rope.contrib import codeassist
    class PatchedPyDocExtractor(codeassist.PyDocExtractor):
        def _get_class_docstring(self, pyclass):
            contents = self._trim_docstring(pyclass.get_doc(), indents=0)
            supers = [super.get_name() for super in pyclass.get_superclasses()]
            doc = 'class %s(%s):\n\n' % (pyclass.get_name(), ', '.join(supers)) + contents

            if '__init__' in pyclass:
                init = pyclass['__init__'].get_object()
                if isinstance(init, pyobjects.AbstractFunction):
                    doc += '\n\n' + self._get_single_function_docstring(init)
            return doc
            
        def _get_single_function_docstring(self, pyfunction):
            signature = self._get_function_signature(pyfunction)
            docs = pyfunction.get_doc()
            docs = self._trim_docstring(pyfunction.get_doc(), indents=0)
            return docs
            return signature + ':\n\n' + docs
    codeassist.PyDocExtractor = PatchedPyDocExtractor 

def getsignaturesfromtext(text, objname):
    """Get object signatures from text (object documentation)
    Return a list containing a single string in most cases
    Example of multiple signatures: PyQt4 objects"""
    return re.findall(objname+r'\([^\)]+\)', text)

def getargsfromtext(text, objname):
    """Get arguments from text (object documentation)"""
    signatures = getsignaturesfromtext(text, objname)
    if signatures:
        signature = signatures[0]
        argtxt = signature[signature.find('(')+1:-1]
        return argtxt.split(',')

def getargsfromdoc(obj):
    """Get arguments from object doc"""
    if obj.__doc__ is not None:
        return getargsfromtext(obj.__doc__, obj.__name__)

def getargs(obj):
    """Get the names and default values of a function's arguments"""
    if inspect.isfunction(obj) or inspect.isbuiltin(obj):
        func_obj = obj
    elif inspect.ismethod(obj):
        func_obj = obj.im_func
    elif inspect.isclass(obj) and hasattr(obj, '__init__'):
        func_obj = getattr(obj, '__init__')
    else:
        return []
    if not hasattr(func_obj, 'func_code'):
        # Builtin: try to extract info from doc
        args = getargsfromdoc(func_obj)
        if args is not None:
            return args
        else:
            # Example: PyQt4
            return getargsfromdoc(obj)
    args, _, _ = inspect.getargs(func_obj.func_code)
    if not args:
        return getargsfromdoc(obj)
    
    # Supporting tuple arguments in def statement:
    for i_arg, arg in enumerate(args):
        if isinstance(arg, list):
            args[i_arg] = "(%s)" % ", ".join(arg)
            
    defaults = func_obj.func_defaults
    if defaults is not None:
        for index, default in enumerate(defaults):
            args[index+len(args)-len(defaults)] += '='+repr(default)
    if inspect.isclass(obj) or inspect.ismethod(obj):
        if len(args) == 1:
            return None
        if 'self' in args:
            args.remove('self')
    return args
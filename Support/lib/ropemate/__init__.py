import os, sys

support_lib = os.path.join(os.environ["TM_SUPPORT_PATH"], "lib")
if support_lib not in sys.path:
    sys.path.insert(0, support_lib)

import tm_helpers

from rope.base import project,libutils

from ropemate.path import update_python_path
from rope.contrib import autoimport

class ropecontext(object):
    """a context manager to have a rope project context"""

    project = None
    resource = None
    input = ""
    
    def __enter__(self):
        project_dir = os.environ.get('TM_PROJECT_DIRECTORY', None)
        file_path = os.environ.get('TM_FILEPATH')
        
        if project_dir:
            self.project = project.Project(project_dir)
            # no use to have auto import for a single file project
            if not os.path.exists("%s/.ropeproject/globalnames" % project_dir):
                importer = autoimport.AutoImport(project=self.project, observe=True)
                importer.generate_cache()
            if os.path.exists("%s/__init__.py" % project_dir):
                sys.path.append(project_dir)
            self.input = sys.stdin.read()
            
        elif file_path:
            #create a single-file project (ignoring all other files in the file's folder)
            folder = os.path.dirname(file_path)
            ignored_res = os.listdir(folder)
            ignored_res.remove(os.path.basename(file_path))
            self.project = project.Project(
                ropefolder=None,projectroot=folder, ignored_resources=ignored_res)
            self.input = sys.stdin.read()
        else:
            tm_helpers.save_current_document()
            file_path = os.environ.get('TM_FILEPATH')
            folder = os.path.dirname(file_path)
            ignored_res = os.listdir(folder)
            ignored_res.remove(os.path.basename(file_path))
            self.project = project.Project(
                ropefolder=None,projectroot=folder, ignored_resources=ignored_res)
            with open(file_path) as fs:
                self.input = fs.read()
            
        self.resource = libutils.path_to_resource(self.project, file_path)
        
        update_python_path( self.project.prefs.get('python_path', []) )
        
        return self
    
    def __exit__(self, type , value , traceback):
        if type is None:
            self.project.close()

context = ropecontext()
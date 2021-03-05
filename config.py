import os.path

app_name = 'DXFer'
company_name = "Autodesk"
default_offset = .1
lib_dir = 'lib'


# ***Ignore Below this line***
app_path = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(app_path, lib_dir, '')

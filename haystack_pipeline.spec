def extra_datas(mydir):
    def rec_glob(p, files):
        import os
        import glob
        for d in glob.glob(p):
            if os.path.isfile(d) and 'py' not in d:
                files.append(d)
            rec_glob("%s/*" % d, files)
    files = []
    rec_glob("%s/*" % mydir, files)
    extra_datas = []
    for f in files:
        extra_datas.append((f, f, 'DATA'))

    return extra_datas


a = Analysis(['haystack_modules/haystack_pipeline.py'],
             pathex=None,
             hiddenimports=None,
             hookspath=None,
             runtime_hooks=None)

a.datas += extra_datas('haystack_modules')

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='haystack_pipeline',
          debug=False,
          strip=None,
          upx=True,
          console=True )
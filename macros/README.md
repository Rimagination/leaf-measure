# Externalized Assets

This repository does not bundle upstream FAMeLeS macro files in the public Option B layout.

To stage upstream assets into a local external assets directory, use:

```powershell
.\scripts\stage-assets.ps1 -SourceRoot "<downloaded-or-extracted-upstream-package>"
```

The default local staging target is:

```text
.\.leaf-measure-assets\
```


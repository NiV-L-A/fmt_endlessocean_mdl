# Important
If you need a script that parses the materials and more, but not the skeleton data, visit https://github.com/NiV-L-A/Endless-Ocean-Files-Converter

# fmt_endlessocean_mdl
- A Noesis plugin to load mdl files from the Endless Ocean serie
- Version: 0.2
- GitHub: https://github.com/NiV-L-A/fmt_endlessocean_mdl
- Author: NiV-L-A
- Special thanks to Hiroshi, Joschka and the people at the XeNTaX discord server
- *If you have any issues, join this discord server and contact NiV-L-A: https://discord.gg/4hmcsmPMDG - Endless Ocean Wiki Server

# Changelog
- Version 0.2 (18/01/2023)
- Meshes get their proprer transformation applied.
- Added the scale component to each object's mat43
- Added the possibility to adjust a mesh's bone coordinates based on the values from its MeshInfo.Origin (added option in settings: AdjustMeshBone)
- Removed by default the "object's Mat43 with bone's Mat43" swap (added option in settings: SwapHiListBoneMat)


- Version 0.1 (12/01/2023)
- Initial Version

# Notes

- !!! Mainly written to understand how the skeleton and the animations work !!!
- The script is intended to be used for .mdl that have skeleton data.
- Can load most skeletons and most animations.
- Loading .mdl files that do not have skeleton data will either give an error or result in an incorrect parsing.
-   If you need a script that parses the materials and more, but not the skeleton data, visit https://github.com/NiV-L-A/Endless-Ocean-Files-Converter
- The values in MOT.Data.TRSPoseValues seems to not be read by the game. Breakpoints do not get hit and changing the values in GAME.DAT does not seem to cause any effect.

# How to install
- Put the fmt_endlessocean_mdl.py file in the noesis/plugins/python folder.

# Demonstration
- https://www.youtube.com/watch?v=XvIQJMB7DG4

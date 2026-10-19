# Records the README GIF and the GitHub social preview image.
# Needs VHS (brew install vhs). Run from the repo root: vhs demo/demo.tape
Output demo/demo.gif

Set Shell "bash"
Set FontSize 18
Set Width 1280
Set Height 640
Set Padding 30
Set Theme "Catppuccin Mocha"
Set TypingSpeed 45ms

Hide
Type "clear"
Enter
Show

Type "bash demo/guard-demo"
Sleep 600ms
Enter
Sleep 11s
Screenshot demo/social-preview.png
Sleep 3s

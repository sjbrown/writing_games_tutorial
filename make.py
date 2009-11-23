#! /usr/bin/env python
import os

s = os.system
s('egrep "<h1|<h2" writing-games.html > /tmp/table.html')
s('''sed -i 's/name=./href="writing-games.html#/g' /tmp/table.html''')

fp = file('table.html', 'w')
fp.write('''\
<html>
<head>
<style>
h1 {
	font-size: small;
}
h2 {
	font-size: smaller;
	text-indent: 4em;
}
h3 {
	font-size: normal;
	text-indent: 8em;
}
</style>
</head>
<body>
''')
fp.close()
s('cat /tmp/table.html >> ./table.html')

s('cd examples; tar -cv --exclude-vcs example2 > example2.tar')
s('cd examples; gzip example2.tar')
s('cd examples; tar -cv --exclude-vcs example3 > example3.tar')
s('cd examples; gzip example3.tar')
s('cd examples; tar -cv --exclude-vcs example4 > example4.tar')
s('cd examples; gzip example4.tar')


# always append a '/' on the src directory when rsyncing
s('rsync -r ./ $DREAMHOST_USERNAME@ezide.com:/home/$DREAMHOST_USERNAME/ezide.com/games')

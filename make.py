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

targen = ('git checkout %(name)s; '
          'cp -a code_examples %(name)s; '
          'tar -cv --exclude-vcs %(name)s > %(name)s.tar; '
          'rm -rf /tmp/%(name)s; '
          'mv %(name)s /tmp/%(name)s; '
          'gzip %(name)s.tar; '
         )
s(targen % {'name': 'example2'})
s(targen % {'name': 'example3'})
s(targen % {'name': 'example4'})

print 'Setting git branch to *master*'
s('git checkout master')

# always append a '/' on the src directory when rsyncing
s('rsync -r ./ $DREAMHOST_USERNAME@ezide.com:/home/$DREAMHOST_USERNAME/ezide.com/games')

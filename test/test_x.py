import xml.etree.ElementTree as et


tree = et.parse('test.xml')
root = tree.getroot()

for child in root:
	print(child.tag, child.attrib)
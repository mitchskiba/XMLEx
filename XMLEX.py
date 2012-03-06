from xml.dom import minidom

dom = minidom.parseString(
"""
<sequence>
<definition name="hex">
    <class values="abcdefABCDEF">
        <digit/>
    </class>
</definition>
<definition name="hexset">
    <multiplicity min="4" max="4">
        <defined name='hex'/>
    </multiplicity>
</definition>
<sequence>
    <line_start/>
    <capture_group name='part1'>
        <defined name='hexset'/>
    </capture_group>
    <literal>-</literal>
    <capture_group name='part2'>
        <defined name='hexset'/>
    </capture_group>
    <literal>-</literal>
    <back_reference name='part1'/>
    <capture_group name='whitespace'>
        <multiplicity min='0'><whitespace/></multiplicity>
    </capture_group>
    <line_end/>
</sequence>
</sequence>
""")


_needs_literal_escape ="[]()\\.^${}|"
_needs_class_escape ="[]^\\"

style = {
    
}

def set_language(lang):
    global style
    if lang=="python" or lang=="pcre":
        style['named_group'] = "(?P<%s>%s)"
        style['named_reference'] = "(?P=%s)"
    elif lang==".NET" or lang=="ruby":
        style['named_group'] = "(?<%s>%s)"
        style['named_reference'] = "\k<%s>"
    
def wrapRender(node):
    return "(?:"+node.render()+")"

def nodeinit(self, xnode):
    self.children = [parse(x) for x in xnode.childNodes if x.nodeType == x.ELEMENT_NODE]
    self.value = ""
    if len(xnode.childNodes) and xnode.firstChild.nodeType == xnode.TEXT_NODE:
        self.value = xnode.firstChild.data

class Literal:
    __init__=nodeinit
    def _sequential(self):
        return True
    def _dir_mult(self):
        return len(self.value)==1
    def render(self):
        return "".join([ ("\\"+x if x in _needs_literal_escape else x) for x in list(self.value)])

class Sequence:
    __init__ = nodeinit
    def _sequential(self):
        return all([child._sequential() for child in self.children])
    def _dir_mult(self):
        return len(self.children)==1 and self.children[0].dir_mult()
    def render(self):
        return "".join([child.render() if child._sequential() else wrapRender(child) for child in self.children])

class Or:
    __init__ = nodeinit
    def _sequential(self):
        return False
    def _dir_mult(self):
        return False
    def render(self):
        return "|".join([child.render() if child._sequential() else wrapRender(child) for child in self.children])

class Multiplicity:
    def __init__(self, xnode):
        self.minvalue = xnode.attributes['min'].value if 'min' in xnode.attributes else "0"
        self.maxvalue = xnode.attributes['max'].value if 'max' in xnode.attributes else ""
        nodeinit(self,xnode)
    def _sequential(self):
        return True
    def _dir_mult(self):
        return False
    def render(self):
        suffix = "{%s,%s}"%(self.minvalue,self.maxvalue)
        if(self.minvalue==self.maxvalue):
            suffix = "{%s}"%self.minvalue
        elif(self.minvalue=="0" and self.maxvalue==""):
            suffix = "*"
        elif(self.minvalue=="1" and self.maxvalue==""):
            suffx = "+"
            
        prefix= self.children[0].render() if self.children[0]._dir_mult() else wrapRender(self.children[0])

        return prefix+suffix
    

class CharacterClass:
    def __init__(self,xnode):
        nodeinit(self,xnode)
        self.values = xnode.attributes['values'].value if "values" in xnode.attributes else ""
        self.values = "".join(["\\"+x if x in _needs_class_escape else x for x in list(self.values)])
        for child in self.children:
            self.values+=child.render()

        self.neg = "negated" in xnode.attributes and xnode.attributes['negated'].value=="true"
    def _dir_mult(self):
        return True
    def _sequential(self):
        return True
    def render(self):
        base = "[^%s]" if self.neg else "[%s]"
        return base%self.values

deffs={}
class Definition:
    def __init__(self,xnode):
        nodeinit(self,xnode)
        deffs[xnode.attributes['name'].value]=self.children[0]
    def _dir_mult(self):
        return True
    def _sequential(self):
        return True
    def render(self):
        return ""

class CaptureGroup:
    def __init__(self,xnode):
        self.name = xnode.attributes['name'].value if 'name' in xnode.attributes else None
        for child in xnode.childNodes:
            if child.nodeType ==child.ELEMENT_NODE:
                self.child = parse(child)
    def _dir_mult(self):
        return True
    def _sequential(self):
        return True
    def render(self):
        global style
        if self.name:
            return style['named_group']%(self.name, self.child.render())
        else:
            return "(%s)"%self.child.render()

class BackRef:
    def __init__(self,xnode):
        self.name = xnode.attributes['name'].value if 'name' in xnode.attributes else None
        self.number = xnode.attributes['number'].value if 'number' in xnode.attributes else None

    def _dir_mult(self):
        return True
    def _sequential(self):
        return True
    def render(self):
        if self.name:
            return style['named_reference']%(self.name)
        elif self.number:
            return "\\%s"%(self.number)

class Defined:
    def __init__(self, xnode):
        self.name = xnode.attributes['name'].value
    def _dir_mult(self):
        return deffs[self.name]._dir_mult()
    def _sequential(self):
        return deffs[self.name]._sequential()
    def render(self):
        return deffs[self.name].render()

def builtin(s):
    class X:
        def __init__(self,xnode):
            pass
        def _dir_mult(self):
            return True
        def _sequential(self):
            return True
        def render(self):
            return s
    return X

def group(prefix):
    class X:
        __init__=nodeinit
        def _dir_mult(self):
            return True
        def _sequential(self):
            return True
        def _render(self):
            return "(%s%s)"%(prefix, children[0].render())

trans = {
    "literal":Literal,
    "sequence":Sequence,
    "or":Or,
    "multiplicity":Multiplicity,
    "whitespace":builtin("\\s"),
    "non_whitespace":builtin("\\S"),
    "digit":builtin("\\d"),
    "non_digit":builtin("\\D"),
    "line_start":builtin("^"),
    "line_end":builtin("$"),
    "string_start":builtin("\\A"),
    "string_end":builtin("\\z"),
    "class":CharacterClass,
    "definition":Definition,
    "defined":Defined,
    "capture_group":CaptureGroup,
    "back_reference":BackRef,
    "ignore_whitespace":group("?-x:"),
    "use_whitespace":group("?x:")
}

def parse(node):
    return trans[node.nodeName](node)

set_language('ruby')
v = parse(dom.firstChild)
print(v.render())

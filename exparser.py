def mkinit(validation=None):
    def init(self, xnode, exparser):
        self.exparser = exparser
        self.children = [exparser.process_dom(x) for x in xnode.childNodes
                         if x.nodeType == x.ELEMENT_NODE]
        self.value = None
        if len(xnode.childNodes)==1 and xnode.firstChild.nodeType == xnode.TEXT_NODE:
            self.value = xnode.firstChild.data

        for propname in xnode.attributes.keys():
            self.__dict__[propname] = xnode.attributes[propname].value
        
        if validation!=None:
            x = validation(self)
            if x:
                raise Exception("%s:%s"%(xnode.nodeName, x))
    return init


_needs_class_escape ="[]^\\"


def wrap(f, out):
    out.write("(?:")
    f(out)
    out.write(")");
class Literal:
    _escape ="[]()\\.^${}|"
    def valid(node):
        if node.value==None or node.children:
            return "Must only have text content"
    __init__ = mkinit(valid)
    _sequential = lambda s: True
    _dirmult = lambda s: len(s.value)==1
    def render(self, out):
        out.write(''.join(["\\"+x if x in Literal._escape else x
                       for x in self.value]))

class Sequence:
    def valid(node):
        if node.value!=None or not node.children:
            return "must have at least one element inside, and no free floating text."
    __init__ = mkinit(valid)
    _sequential = lambda s: all([child._sequential() for child in s.children])
    _dirmult = lambda s: len(s.children)==1 and s.children[0]._dirmult()
    def render(self, out):
        for child in self.children:
            child.render(out) if child._sequential() else wrap(child.render,out)
             
class Or:
    def valid(node):
        if node.value!=None or not node.children:
            return "must have at least one element inside, and no free floating text."
    __init__ = mkinit(valid)
    _sequential = lambda s: False
    _dirmult = lambda s: False
    def render(self, out):
        self.children[0].render(out)
        for child in self.children[1:]:
            out.write('|')
            child.render(out)

class Mult:
    def valid(node):
        node.min = '0' if 'min' not in node.__dict__ else node.min
        node.max = '' if 'max' not in node.__dict__ else node.max
        if node.value!=None or len(node.children)!=1:
            return "must have exactly one child. Optionally min and max \
                        may be specified. (0 or more assued otherwise)."
    __init__=mkinit(valid)
    _sequential = lambda s: True
    _dirmult = lambda s: False
    def render(self, out):
        self.children[0].render(out) if self.children[0]._dirmult() else wrap(self.children[0].render,out)
        if self.min=='0' and self.max=='':
            out.write("*")
        elif self.min=='1' and self.max=='':
            out.write("+")
        elif self.max==self.min:
            out.write("{%s}"%self.min)
        elif self.min=='0' and self.max=='1':
            out.write("?")
        else:
            out.write("{%s,%s}"%(self.min, self.max))

class CharClass:
    _escape = "[]^\\"
    def valid(node):
        for child in node.children:
            if not isinstance(child,CharClass):
                return "Only Character classes can \
                        be children of character classes"
        node.values = "" if 'values' not in node.__dict__ else node.values
        node.values = ''.join(['\\'+x if x in CharClass._escape else x
                               for x in node.values])
        node.negative = 'false' if 'negative' not in node.__dict__ else node.negative
        if node.negative not in ['true','false']:
            return "attribute negative can only be true or false. Default is false"
    __init__=mkinit(valid)
    _sequential = lambda s: True
    _dirmult = lambda s: True
    def render(self,out):
        out.write('[^') if self.negative=='true' else out.write('[')
        out.write(self.values)
        for child in self.children:
            child.render(out)
        out.write(']')
        
def OneShot(string, superclass = object):
    class X(superclass):
        def valid(node):
            if node.children or node.value:
                return "built in character class tags should be self closing"
        __init__=mkinit(valid)
        _sequential = lambda s: True
        _dirmult = lambda s: True
        def render(self, out):
            out.write(string)

    return X

class Macro:
    def valid(node):
        if 'name' not in node.__dict__:
            return "Macros must have names"
        if len(node.children)!=1:
            return "Macros must have one child node"
        node.exparser.defs[node.name] = node.children[0]
        
    __init__=mkinit(valid)
    _sequential = lambda s: True
    _dirmult = lambda s: True
    def render(self,out):
        pass

def UseMacro(xnode, exparser):
    if 'name' not in xnode.attributes:
        raise Exception("use:Macro uses must have a name")
    name = xnode.attributes['name'].value
    if len([child for child in xnode.childNodes if child.nodeType==child.ELEMENT_NODE])!=0:
        raise Exception("use:Macro uses must have no clildren")
    if name not in exparser.defs:
        raise Exception("use:Macro %s undefined"%name)
    return exparser.defs[name]

class SetFlags:
    def valid(node):
        if "flags" not in node.__dict__:
            return "You must specify which flags to set"
        if len(node.children)!=1:
            return "You must provide one regex to have flags set for"
        if set(node.flags).difference('imx'):
            return "Only i,m and x are valid flags to set"
    __init__=mkinit(valid)
    _sequential = lambda s: True
    _dirmult = lambda s: True
    def render(self, out):
        out.write('(?'+self.flags+':')
        self.children[0].render(out)
        out.write(')')

class ClearFlags:
    def valid(node):
        if "flags" not in node.__dict__:
            return "You must specify which flags to clear"
        if len(node.children)!=1:
            return "You must provide one regex to have flags clear for"
        if set(node.flags).difference('imx'):
            return "Only i,m and x are valid flags to clear"
    __init__=mkinit(valid)
    _sequential = lambda s: True
    _dirmult = lambda s: True
    def render(self, out):
        out.write('(?-'+self.flags+':')
        self.children[0].render(out)
        out.write(')')

class Capture:
    def valid(self):
        if self.value or len(self.children)!=1:
            return "Capture groups must have a single regex child"
        if 'name' in self.__dict__:
            self.exparser.refs[self.name]=self.exparser.refc+1
        self.exparser.refc+=1
        
    __init__=mkinit(valid)
    _sequential = lambda s: True
    _dirmult = lambda s: True
    def render(self, out):
        if 'name' in self.__dict__ and self.exparser.keep_names:
            out.write(self.exparser.style['named_group']%self.name)
        else:
            out.write('(')
            
        self.children[0].render(out)
        out.write(')')

class Reference:
    def valid(self):
        if self.value or self.children:
            return 'must have no contents'
        if not (('name' in self.__dict__) ^ ('number' in self.__dict__)):
            return 'must have either name or number specified'
        
        
    __init__=mkinit(valid)
    _sequential = lambda s: True
    _dirmult = lambda s: True
    def render(self, out):
        if 'number' in self.__dict__:
            out.write('\\'+self.number)
        else:
            if self.exparser.keep_names:
                out.write(self.exparser.style['named_reference']%self.name)
            else:
                out.write('\\'+str(self.exparser.refs[self.name]))

class Group:
    _types = {
        "nest":"?>",
        "positive lookahead":"?=",
        "negative lookahead":"?!"
    }
    def valid(self):
        if 'type' not in self.__dict__:
            return "Type must be specified"
        if self.type not in Group._types:
            return "Type must be one of:"+" ".join(
                ["'%s'"%x for x in Group._types.keys()])
        if self.value or len(self.children)!=1:
            return "Group must contain one regex"
    __init__=mkinit(valid)
    _sequential = lambda s: True
    _dirmult = lambda s: True
    def render(self, out):
        out.write('('+Group._types[self.type])
        self.children[0].render(out)
        out.write(')')
        

class ExParser:
    def __init__(self, language="ruby", keep_names = True):
        self.defs = {}
        self.lang = language
        self.style = {}
        self.set_language(language)
        self.refc = 0
        self.refs = {}
        self.keep_names = keep_names
    
    def set_language(self,lang):
        if lang=="python" or lang=="pcre":
            self.style['named_group'] = "(?P<%s>"
            self.style['named_reference'] = "(?P=%s)"
        elif lang==".NET" or lang=="ruby":
            self.style['named_group'] = "(?<%s>"
            self.style['named_reference'] = "\k<%s>"
    
    def process_dom(self, node, root=False):
        if(root):
            self.refc = 0;
            self.refs = {}
            
        return {
            "lit":Literal,
            "seq":Sequence,
            'or':Or,
            'mult':Mult,
            'whitespace':OneShot("\\s",CharClass),
            'not_whitespace':OneShot("\\S",CharClass),
            'digit':OneShot("\\d",CharClass),
            'not_digit':OneShot("\\D",CharClass),
            'word_char':OneShot("\\w",CharClass),
            'not_word_char':OneShot("\\W",CharClass),
            'any':OneShot(".",CharClass),
            'word_boundary':OneShot('\\b'),
            'line_start':OneShot('^'),
            'line_end':OneShot('$'),
            'string_start':OneShot('\\A'),
            'string_end':OneShot('\\z'),
            'class':CharClass,
            'macro':Macro,
            'use':UseMacro,
            'set':SetFlags,
            'clear':ClearFlags,
            'capture':Capture,
            'backref':Reference,
            'group':Group
        }[node.nodeName](node,self)

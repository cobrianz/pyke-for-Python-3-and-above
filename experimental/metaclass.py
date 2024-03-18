from pyke.unique import unique

class metaclass_option1(type): 
    _ignore_setattr = False

    def __init__(self, name, bases, dict):
        print("metaclass: name", name, ", bases", bases, ", dict keys", tuple(sorted(dict.keys())))
        super().__init__(name, bases, dict)
        
    def __call__(self, *args, **kws):
        obj = super().__call__(*args, **kws)
        del obj._ignore_setattr
        print("add instance", obj, "to", self.knowledge_base)
        return obj

class metaclass_option2(type): 

    def __new__(mcl, name, bases, clsdict):
        print("metaclass_option2.__new__: class dict before __new__: name", name, ", bases", bases, 
              ", dict keys", tuple(clsdict.keys()), ", dict values", tuple(clsdict.values()))
        
        def __setattr__(self, attr, value):
            if self.__instance__.get(self, False) :
                if getattr(self, attr) != value:                    
                    print("metaclass.__new__: notify knowledge base", "of attribute change: (%s, %s, %s)" % (self, attr, value))
                    if self.__cls__setattr__ != None:
                        self.__cls__setattr__(attr, value)
                    else:
                        super(self.__class__, self).__setattr__(attr, value)
            else:
                self.__dict__[attr] = value

        def __getattr__(self, name):
            return self.__dict__[name]

        cls__setattr__ = None
        if clsdict.get('__setattr__', None) != None:
            cls__setattr__ = clsdict['__setattr__']
                        
        clsdict['__setattr__'] = __setattr__
        clsdict['__getattr__'] = __getattr__
        clsdict['__cls__setattr__'] = cls__setattr__
        clsdict['__instance__'] = {}    
        
        print("metaclass_option2.__new__: class dict after __new__: name", name, ", bases", bases, 
              ", dict keys", tuple(sorted(clsdict.keys())), ", dict values", tuple(clsdict.values()))
     
        return super().__new__(mcl, name, bases, clsdict)
    

    def __call__(cls, *args, **kws):
        obj = super().__call__(*args, **kws)
        obj.__instance__[obj] = True
        print("add instance of class", cls.__name__, "to knowledge base")        
        return obj


class tracked_object(object):
    __metaclass__ = metaclass_option1
    _not_bound = unique('_not_bound') 

    def __init__(self):
        self._ignore_setattr = True
        self.knowledgebase = None
        
    def __setattr__(self, attr, value):
        print("tracked_object.__setattr__ called on object %s with property %s and value %s" % (self, attr, value))
        if getattr(self, attr, self._not_bound) != value:
            super().__setattr__(attr, value)
            if not hasattr(self, '_ignore_setattr'):
                print("tracked_object.__setattr__: notify", self.knowledge_base, 
                      "of attribute change: (%s, %s, %s)" % (self, attr, value))


class foo_tracked(tracked_object):
     def __init__(self, arg):
         super().__init__()         
         self.prop = arg


class foo_base(object):    
    def __setattr__(self, attr, value):
        print("foo_base.__setattr__ called on object %s with property %s and value %s" % (self, attr, value))
   

class foo_attribute_base(foo_base, metaclass=metaclass_option2):
    def __init__(self, arg):
        super().__init__()         
        self.prop = arg


class foo_attribute(metaclass=metaclass_option2):
    def __init__(self, arg):
        super().__init__()         
        self.prop = arg
         
    def __setattr__(self, attr, value):
        print("foo_attribute.__setattr__ called on object %s with property %s and value %s" % (self, attr, value))
   
                      
class foo(metaclass=metaclass_option2):
     def __init__(self, arg):
         super().__init__()         
         self.prop = arg
         
     def foo_method(self):
        print("foo_method called")

def test_foo_option2():
    f1 = foo(1) 
    f1.prop = 2 
    
    f2 = foo("egon")  
    f2.prop = "ralf"  

    f3 = foo_attribute(3)
    f3.prop = 4
    
    f4 = foo_attribute("karin")
    f4.prop = "sabine"
    
    f5 = foo_attribute_base(5)
    f5.prop = 6
    
    f6 = foo_attribute_base("sebastian")
    f6.prop = "philipp"

    
def test_foo_option1():
    import sys
    import doctest
    sys.exit(doctest.testmod(optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE)[0])

if __name__ == "__main__":
    test_foo_option2()

from boolparser import BooleanParser, TokenType
from tseitin_generator import *

# var_dict={"a":True, "b":False, "c":False, "d":True, "e":True}
# p = BooleanParser('(a || b) && c || !(d && e)')
# p.printTree(p.root)
# print(p.evaluate(var_dict))
# print(p.toString())

formulas = [
    '(a || b) && c || !(d && e)',
    '(!(p && (q || !r)))',
    '(a && b) || (a && !c)'
]

for test_id, formula in enumerate(formulas, start = 1):
    print("\n=============== TEST %d ===============\n" % (test_id))
    f = TseitinFormula(formulas[1])
    f.toCNF()
    print(f.toString())

    if test_id == 1:
        f.exportToFile()
print()
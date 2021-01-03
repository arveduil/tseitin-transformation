from bparser.boolparser import BooleanParser
from bparser.tseitin_generator import TseitinFormula
from flask import Flask, request
from flask_restful import Api, Resource, reqparse, abort, fields, marshal_with

def simple_tests():
    formulas = {
        '(a || b) && c || !(d && e)': 'string',
        # '(!(p && (q || !r)))': 'string',
        # '(a && b) || (a && !c)': 'string',
        # '(a && b) or ((c || d) and e)': 'string',
        # './src/data/simple_dnf_0.dnf': 'file',
        # './src/data/formula.txt': 'file',
        # 'a and !a': 'string',
        # '!x1 and x2 or x1 and !x2 or !x2 and x3': 'string',
        # '!a and a': 'string'
    }

    for test_id, (formula_value, formula_format) in enumerate(formulas.items()):
        print("\n=============== TEST %d ===============\n" % (test_id))

        # file_name = "simple_cnf_" + str(test_id)
        # formula = TseitinFormula(
        #     formula=formula_value, formula_format=
        #     , export_to_file=True, export_file_name=file_name)


        # only for debug purposes
        # print(formula.getSolverReport())
        return (formula.getCNF())

#
# def advanced_test():
#     print("\n=============== ADVANCED TEST ===============\n")
#
#     files_map = {
#         0: 'src/data/easy-sat-0.cnf',
#         1: 'src/data/easy-sat-1.cnf',
#         2: 'src/data/easy-unsat-0.cnf',
#         3: 'src/data/easy-unsat-1.cnf',
#         4: 'src/data/medium-sat-0.cnf',
#         5: 'src/data/medium-sat-1.cnf',
#         6: 'src/data/medium-sat-2.cnf',
#         7: 'src/data/medium-sat-3.cnf',
#         8: 'src/data/medium-unsat-0.cnf',
#         9: 'src/data/medium-unsat-1.cnf',
#         10: 'src/data/medium-unsat-2.cnf',
#         11: 'src/data/medium-unsat-3.cnf',
#         12: 'src/data/hard-sat-0.cnf',
#         13: 'src/data/hard-sat-1.cnf',
#         14: 'src/data/hard-sat-2.cnf',
#         15: 'src/data/hard-sat-3.cnf',
#         16: 'src/data/hard-unsat-0.cnf',
#         17: 'src/data/hard-unsat-1.cnf',
#         18: 'src/data/hard-unsat-2.cnf',
#         19: 'src/data/hard-unsat-3.cnf',
#         20: 'src/data/very-hard-sat.cnf',
#         21: 'src/data/very-hard-unsat.cnf'
#     }
#
#     input_file_name = files_map[21]
#     _ = TseitinFormula(formula=input_file_name,
#                        formula_format='file', export_to_cnf_file=True, debug=True)

app = Flask(__name__)
api = Api(app)

def getTseitinResponse(formula_value):
    formula = TseitinFormula(
        formula=formula_value, formula_format='string', export_to_cnf_file=False, debug=True, interrupt_time=4,
        return_all_assignments=True)

    terms, clauses, res = formula.getCNF()
    return {
        "terms": terms,
        "clauses": clauses,
        "dimacs": res
    }


@app.route('/', methods=['GET', 'POST']) #allow both GET and POST requests
def tseitin():
    if request.method == 'GET': #this block is only entered when the form is submitted
        formula_value = '(a || b) && c || !(d && e)'
        return getTseitinResponse(formula_value)

    formula_value = request.get_json()['cnf']
    return getTseitinResponse(formula_value)




#api.add_resource(TseitinApi,"/")

if __name__ == "__main__":
    app.run(debug=True)




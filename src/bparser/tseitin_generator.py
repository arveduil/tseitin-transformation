from bparser.boolparser import BooleanParser
from solver.SATSolver import SATSolver
from utils import tseitin_conversions as tc
from collections import deque, defaultdict
from datetime import datetime
import os
import csv
import re
import io


class TseitinFormula:
    def __init__(self, formula, formula_format="string", export_to_cnf_file=False, debug=False, use_solver=True,
                 solver_name='m22', return_all_assignments=False, use_timer=True, interrupt_time=None):

        self.inputFile = None
        self.root = None
        self.debug = debug

        # list of all clauses based on tree
        # every clause is a list, where:
        # id = 0: first term or index of another clause
        # id = 1: operator id
        # id = 2: second term or index of another clause
        self.clauses = []

        self.original_terms = []

        # list of all terms in expression
        self.terms = {}

        # ids of last clause for left and right tree, it is necessary to get the last clause
        self.last_clause_ids = []

        # formatted dict of all clauses
        # keys: clause name, for example phi0
        # values: dict with keys 'first_term', 'second_term', 'operator', 'is_negated'
        self.clause_map = {}

        self.terms_assignment = {}
        self.execution_time_str = '--'

        # solver params
        self.solver_name = solver_name
        self.return_all_assignments = return_all_assignments
        self.use_timer = use_timer

        if formula_format == 'string':
            self.original_formula = formula
        elif formula_format == 'file':
            self.original_formula = self.getFormulaFromFile(
                formula, debug=debug)
            self.inputFile = formula
        else:
            raise RuntimeError(
                "Unsupported formula format. You can use one of following options: string, file.")

        # parse tree
        if self.debug:
            print("Parsing formula...")
        self.tree = BooleanParser(self.original_formula)
        self.root = self.tree.root
        if self.debug:
            print("Parsing complete!\n")

        self.toCNF()

        if use_solver:
            self.solve(solver_name=self.solver_name, return_all_assignments=self.return_all_assignments,
                       use_timer=self.use_timer, interrupt_time=interrupt_time)

        if export_to_cnf_file:
            if self.debug:
                print("Export formula to CNF file...")
            self.export2CNF()
            if self.debug:
                print("Successful data export!\n")

    def toCNF(self):
        if self.debug:
            print("Converting data to Tseitin formula...")

        self.toTseitinClauses(self.root)
        self.getTseitinClauses()
        self.setTseitinFormula()

        if self.debug:
            print("Converting complete!\n")

    def toTseitinClauses(self, node):
        var_token = self.tree.tokenizer.getToken('var')
        nodestack = deque()
        current = node
        previous = None

        while True:
            while current != None and current.tokenType != var_token:
                if current.right != None and current.right.tokenType != var_token:
                    nodestack.append((current, current.right))
                nodestack.append((previous, current))

                previous = current
                current = current.left

            (previous, current) = nodestack.pop()

            if current.right != None and current.right.tokenType != var_token and len(nodestack) > 0 and nodestack[-1][1] == current.right:
                nodestack.pop()
                nodestack.append((previous, current))
                previous = current
                current = current.right
            else:
                # build clause
                clause = []

                if current == self.root:
                    clause = [None, current.tokenType, None, current.negate]

                    if len(self.last_clause_ids) != 2:
                        if current.left.negate == True or current.left.tokenType == var_token:
                            # left child is a term
                            if current.left.negate:
                                self.clauses.append(
                                    self.getNegatedTermClause(current.left))
                                clause[0] = len(self.clauses)-1
                            else:
                                clause[0] = current.left.value
                        else:
                            # left child is an operator
                            clause[0] = self.last_clause_ids[0]

                        if current.right.negate == True or current.right.tokenType == var_token:
                            # right child is a term
                            if current.right.negate:
                                self.clauses.append(
                                    self.getNegatedTermClause(current.right))
                                clause[2] = len(self.clauses)-1
                            else:
                                clause[2] = current.right.value
                        else:
                            # right child is an operator
                            clause[2] = self.last_clause_ids[0]
                    else:
                        # both leaves of root node are operators
                        clause[0] = self.last_clause_ids[0]
                        clause[2] = self.last_clause_ids[1]
                else:
                    if current.left.value == None:
                        clause.append(len(self.clauses)-1)
                    else:
                        if current.left.negate:
                            self.clauses.append(
                                self.getNegatedTermClause(current.left))
                            clause.append(len(self.clauses)-1)
                        else:
                            clause.append(current.left.value)

                    clause.append(current.tokenType)

                    if current.right.value == None:
                        clause.append(len(self.clauses)-1)
                    else:
                        if current.right.negate:
                            self.clauses.append(
                                self.getNegatedTermClause(current.right))
                            clause.append(len(self.clauses)-1)
                        else:
                            clause.append(current.right.value)

                    clause.append(current.negate)
                self.clauses.append(clause)

                if previous == self.root:
                    self.last_clause_ids.append(len(self.clauses)-1)

                previous = current
                current = None

            if len(nodestack) <= 0:
                break

    def getNegatedTermClause(self, node):
        token = self.tree.tokenizer.getToken('not')
        return [
            node.value, token, None, False
        ]

    def getTseitinClauses(self):
        i = 0

        for clause in self.clauses:
            logic_var = "phi" + str(i)
            first_term, second_term = "", ""

            if isinstance(clause[0], int):
                first_term = "phi" + str(clause[0])
            else:
                first_term = clause[0]
                self.original_terms.append(first_term)

            if isinstance(clause[2], int):
                second_term = "phi" + str(clause[2])
            else:
                second_term = clause[2]
                self.original_terms.append(second_term)

            operator, is_negated = clause[1], clause[3]
            if operator == 'AND' and is_negated:
                operator = "NAND"
            elif operator == 'OR' and is_negated:
                operator = 'NOR'

            self.clause_map[logic_var] = {
                "first_term": first_term,
                "second_term": second_term,
                "operator": operator
            }

            i += 1

    def setTseitinFormula(self):
        clauses = []
        terms = []

        for clause, definition in self.clause_map.items():
            operator = definition['operator']

            if operator == 'NOT':
                term_list = [definition['first_term'], clause]
            else:
                term_list = [definition['first_term'],
                             definition['second_term'], clause]
            terms.extend(term_list)

            if operator == 'AND':
                clauses.extend(tc.getTseitinAndClause(term_list))
            elif operator == 'NAND':
                clauses.extend(tc.getTseitinNandClause(term_list))
            elif operator == 'OR':
                clauses.extend(tc.getTseitinOrClause(term_list))
            elif operator == 'NOR':
                clauses.extend(tc.getTseitinNorClause(term_list))
            elif operator == 'NOT':
                clauses.extend(tc.getTseitinNotClause(term_list))

        # append the last variable as clause
        clauses.append([clause])

        # removes duplicates from terms list
        self.terms = dict.fromkeys(terms)
        idx = 0
        for t in self.terms:
            self.terms[t] = idx
            idx += 1
        self.clauses = clauses

    def getTseitinFormulaStr(self, split=True):
        tseitin_formula = []
        for clause in self.clauses:
            term_str = "("

            for term in clause:
                if term == -1:
                    term_str += "!"
                else:
                    term_str = term_str + term + " or "

            # remove last 'or'
            term_str = term_str[:-4]
            term_str = term_str + ")"

            tseitin_formula.append(term_str + " and ")

        tseitin_formula[-1] = tseitin_formula[-1][:-5]
        if split:
            for part in tseitin_formula:
                part = part.replace("and ", "and\n")

        return "".join(tseitin_formula)

    def toString(self):
        return self.getTseitinFormulaStr(split=False)

    # export Tseitin CNF form to .cnf file
    def export2CNF(self):
        clauses_num = len(self.clauses)
        terms_num = len(self.terms)

        script_path = os.path.dirname(__file__)
        os_sep = os.sep
        path_list = script_path.split(os.sep)
        script_directory = path_list[0:len(path_list)-1]

        file_name = f'{datetime.now().strftime("%d_%m_%Y_%H_%M_%S")}_data.cnf'
        rel_path = f'data{os_sep}{file_name}'
        path = f'{os_sep.join(script_directory)}{os_sep}{rel_path}'

        with open(path, "w+") as file:
            file.write(f'c {file_name}\n')
            if self.inputFile:
                file.write(f'c formula input file: {self.inputFile}\n')
            file.write("c\n")
            file.write(f'p cnf {terms_num} {clauses_num}')

            clauses = []
            for clause in self.clauses:
                formatted_clause_list = []
                for idx, term in enumerate(clause):
                    if term == -1:
                        continue

                    term_id = self.terms[term] + 1
                    if idx > 0 and clause[idx-1] == -1:
                        term_id *= -1

                    formatted_clause_list.append(term_id)

                formatted_clause_list.append(0)
                clauses.append(" ".join([str(i)
                                         for i in formatted_clause_list]))

            file.write('\n'.join(map(str, clauses)))

    def getCNF(self):
        clauses_num = len(self.clauses)
        terms_num = len(self.terms)

        script_path = os.path.dirname(__file__)
        os_sep = os.sep
        path_list = script_path.split(os.sep)
        script_directory = path_list[0:len(path_list) - 1]
        clauses = []
        for clause in self.clauses:
            formatted_clause_list = []
            for idx, term in enumerate(clause):
                if term == -1:
                    continue

                term_id = self.terms[term] + 1
                if idx > 0 and clause[idx - 1] == -1:
                    term_id *= -1

                formatted_clause_list.append(term_id)

            formatted_clause_list.append(0)
            clauses.append(" ".join([str(i)
                                     for i in formatted_clause_list]))

       # file.write('\n'.join(map(str, clauses)))
        print(self.clause_map)
        tseitin_formula = self.getTseitinFormulaStr(split=False)
        original_terms_num = len(self.original_terms)
        tseitin_terms_num = len(self.terms)
        return ( terms_num,
                 clauses_num,
                 ' '.join(map(str, clauses)),
                 tseitin_formula,
                 original_terms_num,
                 tseitin_terms_num
                 #,     self.clause_map
                 )

    def solve(self, solver_name='m22', return_all_assignments=True, use_timer=True, interrupt_time=None):
        if self.debug:
            print("Solving in progress...")

        solver_data = SATSolver(
            self.terms, self.clauses).solve(solver_name, return_all_assignments, use_timer, interrupt_time=interrupt_time)

        self.execution_time_str = solver_data['execution_time']
        self.terms_assignment = solver_data['terms_assignment']

        if self.debug:
            print("Solver is done!\n")

    def getTermsAssignment(self, only_original=True):
        if only_original:
            terms_assignment = list()
            p = re.compile('phi*')
            for assignment in self.terms_assignment:
                part_assignment = dict()
                for term, value in assignment.items():
                    if not p.match(term):
                        part_assignment[term] = value

                terms_assignment.append(part_assignment)
            return terms_assignment
        else:
            return self.terms_assignment

    def getFormulaFromFile(self, filepath, debug=True):
        _, file = os.path.split(filepath)
        extension = file.split(".")[-1]

        if extension not in ["txt", "cnf", "dnf"]:
            raise RuntimeError(
                f'Not supported file extension: \'{extension}\'...')

        if debug:
            print(f'Loading data from file: \'{file}\'...')

        if extension == "txt":
            formula = self.getFromulaFromTxt(filepath)
        elif extension in ["cnf", "dnf"]:
            formula = self.getFormulaFromDIMAC(filepath)

        if debug:
            print("The data has been loaded!\n")

        return formula

    def getFormulaFromDIMAC(self, filepath):
        with open(filepath, 'r') as file:
            initial_lines = True
            subformulas_list = []
            for line in file:
                subformula = ""
                if initial_lines:
                    # skip comment lines
                    if line[0] == 'c':
                        continue
                    # check if file is truly a dnf or cnf file inside and switch flag to formula processing
                    elif line[0] == 'p' and line[2:5] in ["cnf", "dnf"]:
                        initial_lines = False
                    else:
                        raise RuntimeError(
                            "Intial file lines do not follow DNF or CNF syntax.")
                else:
                    # variable used to concatenate digits of variable numbers higher than 9
                    variable_number = ""
                    try_to_place_and = False
                    expect_number = False
                    expect_minus_or_number = False
                    for character in line:
                        # check if loaded character is of expected type
                        if expect_minus_or_number and not (character == '-' or character.isdigit()):
                            raise RuntimeError("Syntax error in clause line.")
                        else:
                            expect_minus_or_number = False

                        if expect_number and not character.isdigit():
                            raise RuntimeError("Syntax error in clause line.")
                        else:
                            expect_number = False

                        # if there was an ongoing concatenation of digits but next character is not digit anymore
                        if variable_number != "" and not character.isdigit():
                            # it should be whitespace, if so, add a variable called userdefX, where X is concatenated number, to the formula
                            if character != ' ':
                                raise RuntimeError(
                                    "Syntax error in clause line.")
                            subformula = subformula + " userdef" + variable_number + " "
                            variable_number = ""

                        # if the whitespace that caused "and placing" was before next variable and not line-ending zero, the placing should happen
                        if try_to_place_and and character != '0':
                            subformula += " and "
                        try_to_place_and = False

                        if character == '-':
                            subformula += " not "
                            # minus should be followed by variable number
                            expect_number = True
                        elif character == ' ':
                            try_to_place_and = True
                            # whitespace should be followed by minus, variable number or line-ending zero
                            expect_minus_or_number = True
                        elif character.isdigit():
                            if character == '0' and variable_number == "":
                                subformulas_list.append(subformula)
                                break
                            variable_number += character
                        else:
                            raise RuntimeError("Syntax error in clause line.")

        # while returning, cut off the ending containing " or " caused by the last endline
        return " or ".join(subformulas_list)

    # TODO: validate formula
    def getFromulaFromTxt(self, filepath):
        with open(filepath, 'r') as file:
            line_list = []
            for line in file:
                line_list.append(f'{line.strip()} ')

        return "".join(line_list)

    def getSolverReport(self):
        report = []

        original_terms = list(set(self.original_terms))
        original_terms = [x for x in original_terms if x != None]
        tseitin_formula = self.getTseitinFormulaStr(split=False)
        original_terms_num = len(original_terms)
        tseitin_terms_num = len(self.terms)
        total_terms_num = original_terms_num + tseitin_terms_num

        report = [
            "Original formula:\n" + self.original_formula,
            "\n\nTseitin formula:\n" + tseitin_formula,
            "\n\nOriginal number of terms:\n" + str(original_terms_num),
            "\n\nTseitin number of terms:\n" + str(tseitin_terms_num),
            "\n\nTotal number of terms:\n" + str(total_terms_num),
            "\n\nTotal number of clauses:\n" + str(len(self.clauses)),
            "\n\nExecution time:\n" + self.execution_time_str,
            "\n\nTerms assignment:\n"
        ]

        for terms_assignment in self.getTermsAssignment():
            report.append(str(terms_assignment) + "\n")

        return "".join(report)

    def exportReport2CSV(self):
        if self.debug:
            print("Saving report to CSV file...")

        original_terms = list(set(self.original_terms))
        original_terms = [x for x in original_terms if x != None]
        original_terms_num = len(original_terms)
        tseitin_terms_num = len(self.terms)
        total_terms_num = original_terms_num + tseitin_terms_num

        report_summary = [
            ["File name", self.inputFile if None else "--"],
            ["Original number of terms", original_terms_num],
            ["Tseitin number of terms", tseitin_terms_num],
            ["Total number of terms", total_terms_num],
            ["Total number of clauses", len(self.clauses)],
            ["Execution time", self.execution_time_str],
            ["Terms assignment"]
        ]

        report_data = defaultdict(list)
        for terms_assignment in self.getTermsAssignment():
            for term, value in terms_assignment.items():
                report_data[term].append(value)

        with open('src/data/report.csv', 'w') as file:
            writer = csv.writer(file)
            writer.writerows(report_summary)

            for term, values in report_data.items():
                writer.writerow([term] + values)

        if self.debug:
            print("Report was saved successfully!\n")

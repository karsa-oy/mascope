import unittest

from lib.molmass import Formula


ions = [
    # (formula [str], charge [int], m/z [float])
    ("Br-", -1, 78.9188861799),
    ("H3O+", +1, 19.0178411385),
    # isotopes
    ("[81Br]-", -1, 80.9168382799091),
    #
    # parenthesis
    ("([81Br])-", -1, 80.9168382799091),
    ("(Br)2-", -1, 157.8372237799),
    #
    # multi-charge
    ("Br_2-", -2, 39.45971738),
    ("Br2-", -1, 157.8372237799),
    #
    # arithmetics
    ("H2O+Br-", -1, 96.9294508662),
    ("(H2O)+Br-", -1, 96.9294508662),
    ("H2O+H2O+Br-", -1, 114.9400155525),
    ("(H2O)2+Br-", -1, 114.9400155525),
    ("H2O+H2O+Br-", -1, 114.9400155525),
    # ('H2O-H2O+Br-', -1, 78.9188861799), # TODO: Fails due to + evaluated prior to -
    ("(H2O-OH)Br-", -1, 79.926711212),
    # ('(H2O-H2O)Br-', -1, 79.926711212), # TODO Fails due to "Empty formula error"
    #
]


class TestMolMass(unittest.TestCase):

    def test_mz(self):
        global ions

        for formula, charge, mz in ions:
            f = Formula(formula)
            self.assertEqual(f.charge, charge)
            self.assertAlmostEqual(f.mz, mz, places=7)


if __name__ == "__main__":
    unittest.main()

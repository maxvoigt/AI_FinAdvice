# Asset parameter dictionary for FP investment advice and reference.
# Only the necessary columns (p_up, x_up, x_down) are included here.
# p_up is given as a decimal (e.g., 0.5 for 50%)
# x_up and x_down are given as decimals (e.g., 0.3 for +30%, -0.1 for -10%)

# Update assetDictionary with new values from previous 'assets' definition
assetDictionary = {
    1: {
        "name": "IndAsset",
        "desc": "Symmetric baseline",
        "p_up": 0.50,
        "x_up": 0.25,
        "x_down": -0.15,
    },
    2: {
        "name": "Dominated",
        "desc": "Lower mean",
        "p_up": 0.50,
        "x_up": 0.15,
        "x_down": -0.25,
    },
    3: {
        "name": "PosSkew",
        "desc": "Right-skewed",
        "p_up": 0.20,
        "x_up": 0.45,
        "x_down": -0.05,
    },
    4: {
        "name": "NegSkew",
        "desc": "Left-skewed",
        "p_up": 0.80,
        "x_up": 0.15,
        "x_down": -0.35,
    },
    5: {
        "name": "Hedge",
        "desc": "Corr with Asset 1",
        "p_up": 0.50,
        "x_up": 0.25,
        "x_down": -0.15,
    },
}

correlationCoefficient = -0.5

### Old values --> replaced because the positively skewed asset dominates cash
'''

assetDictionary = {
    1: {
        "name": "IndAsset",
        "desc": "Symmetric baseline",
        "p_up": 0.5,
        "x_up": 0.3,
        "x_down": -0.1,
    },
    2: {
        "name": "Dominated",
        "desc": "Lower mean",
        "p_up": 0.5,
        "x_up": 0.2,
        "x_down": -0.2,
    },
    3: {
        "name": "Pos. Skew",
        "desc": "Right-skewed",
        "p_up": 0.2,
        "x_up": 0.5,
        "x_down": 0.0,
    },
    4: {
        "name": "Neg. Skew",
        "desc": "Left-skewed",
        "p_up": 0.8,
        "x_up": 0.2,
        "x_down": -0.3,
    },
    5: {
        "name": "Hedge",
        "desc": "Corr with Asset 1",
        "p_up": 0.5,
        "x_up": 0.3,
        "x_down": -0.1,
    },
}
'''

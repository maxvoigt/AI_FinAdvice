# Asset parameter dictionary for FP investment advice and reference.
# Only the necessary columns (p_up, x_up, x_down) are included here.
# p_up is given as a decimal (e.g., 0.5 for 50%)
# x_up and x_down are given as decimals (e.g., 0.3 for +30%, -0.1 for -10%)

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

correlationCoefficient = -0.5
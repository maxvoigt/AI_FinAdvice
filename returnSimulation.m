clear all; clc; 

% This script generates the returns / prices for the assets used for the
% experiment in Financial Advice with AI by d'Astous and Voigt

% The distribution of returns is calibrated using Ebert (2015)


%% Define parameters

assets = [
    0.06   0.20^2   0; % E, V, S
    0.05   0.20^2   0;
    0.06   0.20^2   1;
    0.06   0.20^2   -1
];
% asset 5 is perfectly negatively correlated with asset 1 by reversing the
% event space

%% Draw returns
N = 1000;
T = 24;

assetReturns = nan(T, N, 5);
outputParameters = nan(size(assets));

for asset=1:4
    E = assets(asset,1); V = assets(asset,2); S = assets(asset,3);
    
    p = 0.5;
    if S > 0
        p = (4 + S.^2 + sqrt(S.^4 + 4 * S.^2)) ./ (8 + 2 * S.^2);
    elseif S < 0
        p = (4 + S.^2 - sqrt(S.^4 + 4 * S.^2)) ./ (8 + 2 * S.^2);
    end

    x_1 = E + sqrt(V * (1-p) ./ p);
    x_2 = E - sqrt(V * p ./ (1-p)); 

    disp([asset, p, x_1, x_2])

    outputParameters(asset,1) = p;
    outputParameters(asset,2) = x_1;
    outputParameters(asset,3) = x_2;
    
    tmpReturns = rand(T, N);
    
    x1_Index = tmpReturns <= p;

    tmpReturns(x1_Index) = x_1;
    tmpReturns(~x1_Index) = x_2;

    assetReturns(:,:,asset) = tmpReturns;

    if asset == 1
        % Perfect negatively correlated
        tmpReturns(x1_Index) = x_2;
        tmpReturns(~x1_Index) = x_1;

        assetReturns(:,:,5)= tmpReturns;
    end
end

% Generate prices
assetPrices = 100 * ones(T+1, N, 5);

for t = 2:T+1
    assetPrices(t,:,:) = assetPrices(t-1,:,:) .* (1 + assetReturns(t-1,:,:));
end

assetPrices = round(assetPrices, 2);

A = permute(assetPrices, [2, 1, 3]);   % now size: N x (T+1) x 5

% Then, reshape to combine time and asset dimensions
A = reshape(A, N, (T+1)*5);


%% Output
writematrix(A, './_static/global/assetPrices.csv');
writematrix(outputParameters, './_static/global/assetParameters.csv');
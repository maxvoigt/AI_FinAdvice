// Load variables
const INV_INPUT_STYLE = {
    width: '80px',
    minWidth: '80px',
    maxWidth: '80px',
    flex: '0 0 80px',
};

/** Delay before `liveSend` after the user pauses typing in portfolio-share / holdings fields. */
const LIVE_NUMERIC_INPUT_DEBOUNCE_MS = 200;

/** Epsilon for comparing last live-sent numeric vs next flush (debounce + blur). */
const NUMERIC_LIVE_SEND_EPS = 1e-6;

const options = js_vars.investmentOptions;
const riskFreeAsset = (js_vars.riskFreeAsset && js_vars.riskFreeAsset[0]) || {};

const DEFAULT_LIVE_PORTFOLIO = {
    dollarHoldings: [0, 0, 0, 0, 0, 10000],
    numShares: [0, 0, 0, 0, 0, 10000],
    allocation: [0, 0, 0, 0, 0, 100],
};

const initialPortfolioState = js_vars.initialPortfolio || DEFAULT_LIVE_PORTFOLIO;

const isAdvisor = js_vars.isAdvisor || false;

function InvModule({ pageStatus, phase }) {
    const [livePortfolio, setLivePortfolio] = React.useState(initialPortfolioState);

    const shareTimersRef = React.useRef({});
    const holdingsTimersRef = React.useRef({});
    const lastLiveSentShareRef = React.useRef({});
    const lastLiveSentHoldingsRef = React.useRef({});
    const [shareDraftByAsset, setShareDraftByAsset] = React.useState({});
    const [holdingsDraftByAsset, setHoldingsDraftByAsset] = React.useState({});

    const flushSetSharesInput = React.useCallback((num, raw) => {
        const v = parseFloat(String(raw).trim(), 10);
        if (Number.isNaN(v)) return;
        const prev = lastLiveSentShareRef.current[num];
        if (prev !== undefined && Math.abs(v - prev) <= NUMERIC_LIVE_SEND_EPS) return;
        lastLiveSentShareRef.current[num] = v;
        setShares(num, v);
    }, []);

    const debouncedSetSharesInput = React.useCallback(
        (num, raw) => {
            const timers = shareTimersRef.current;
            if (timers[num]) clearTimeout(timers[num]);
            timers[num] = setTimeout(() => {
                flushSetSharesInput(num, raw);
                delete timers[num];
            }, LIVE_NUMERIC_INPUT_DEBOUNCE_MS);
        },
        [flushSetSharesInput],
    );

    const flushSetHoldingsInput = React.useCallback((num, raw) => {
        const v = parseFloat(String(raw).trim(), 10);
        if (Number.isNaN(v)) return;
        const prev = lastLiveSentHoldingsRef.current[num];
        if (prev !== undefined && Math.abs(v - prev) <= NUMERIC_LIVE_SEND_EPS) return;
        lastLiveSentHoldingsRef.current[num] = v;
        sendHoldingsLive(num, v);
    }, []);

    const debouncedSetHoldingsInput = React.useCallback(
        (num, raw) => {
            const timers = holdingsTimersRef.current;
            if (timers[num]) clearTimeout(timers[num]);
            timers[num] = setTimeout(() => {
                flushSetHoldingsInput(num, raw);
                delete timers[num];
            }, LIVE_NUMERIC_INPUT_DEBOUNCE_MS);
        },
        [flushSetHoldingsInput],
    );

    React.useEffect(() => {
        return () => {
            Object.values(shareTimersRef.current).forEach(clearTimeout);
            shareTimersRef.current = {};
            Object.values(holdingsTimersRef.current).forEach(clearTimeout);
            holdingsTimersRef.current = {};
        };
    }, []);

    React.useEffect(() => {
        const apply = (payload) => {
            if (!payload || !payload.portfolio) return;
            const p = payload.portfolio;
            setLivePortfolio(p);
        };
        window.invModuleApplyLivePayload = apply;
        return () => {
            if (window.invModuleApplyLivePayload === apply) {
                window.invModuleApplyLivePayload = function () {};
            }
        };
    }, []);


    React.useEffect(() => {
        if (pageStatus !== 'New') return undefined;
        for (let i = 1; i <= 5; i++) {
            $('#newPrice' + i).addClass('table-info');
        }
        const t = window.setTimeout(() => {
            for (let i = 1; i <= 5; i++) {
                $('#newPrice' + i).removeClass('table-info');
            }
        }, 1000);
        return () => {
            window.clearTimeout(t);
            for (let i = 1; i <= 5; i++) {
                $('#newPrice' + i).removeClass('table-info');
            }
        };
    }, [pageStatus]);

    const canEdit =
        (js_vars.isAdvisor && !js_vars.isInvestRound)
            ? false
            : ((pageStatus === 'New' && phase === 'Investment'));
    
    let totalOld =
        options.reduce((a, o) => a + o.oldValue, 0) + (riskFreeAsset.currentValue || 0);
    let totalNew =
        options.reduce((a, o) => a + (Number(o.newValue) || 0), 0) + (Number(riskFreeAsset.newValue) || 0);
    if (js_vars.currentPeriod === js_vars.firstRound) {
        totalNew = totalOld;
    }
    const valueTotalLeft = pageStatus === 'Old' ? totalOld : totalNew;

    return (
        <div className="d-flex gap-3 align-items-stretch">
            <div className="card flex-grow-1">
                <div className="card-body p-2">
                    <div className="inv-table-scroll">
                    <table className="table table-sm table-striped table-hover align-middle mb-0 text-center">
                        <thead>
                            <tr>
                                <th colSpan="2" style={{ borderBottom: 'none' }} />
                                <th colSpan="3">{js_vars.lang == 'en' ? 'Current' : 'Actuel'}</th>
                                <th style={{ width: '2px', border: 'none', background: 'transparent' }} />
                                <th colSpan="3">{js_vars.lang == 'en' ? 'New' : 'Nouveau'}</th>
                            </tr>
                            <tr>
                                <th></th>
                                <th> {js_vars.lang == 'en' ? 'Price ($)' : 'Prix ($)'} </th>
                                <th>{js_vars.lang == 'en' ? 'Holdings' : 'Positions'}</th>
                                <th style={{ whiteSpace: 'nowrap' }}>{js_vars.lang == 'en' ? 'Value ($)' : 'Valeur ($)'}</th>
                                <th>
                                    {js_vars.lang == 'en' ? 'Share (%)' : 'Part (%)'}
                                </th>
                                <th> </th>
                                <th>{js_vars.lang == 'en' ? 'Holdings' : 'Positions'}</th>
                                <th style={{ whiteSpace: 'nowrap' }}>{js_vars.lang == 'en' ? 'Value ($)' : 'Valeur ($)'}</th>
                                <th>
                                    {js_vars.lang == 'en' ? 'Share (%)' : 'Part (%)'}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {options.map((option, idx) => {
                                const num = option.num;
                                const priceLeft = pageStatus === 'Old' ? option.oldPrice : option.newPrice;
                                const valueLeft = pageStatus === 'Old' ? option.oldValue : option.newValue;
                                const shareLeft = pageStatus === 'Old' ? option.oldWealthShare : option.newWealthShare;
                                const priceCellId = pageStatus === 'New' ? 'newPrice' + num : undefined;
                                const pv = livePortfolio.dollarHoldings[idx];
                                const sh = livePortfolio.allocation[idx];
                                const shareInputStr =
                                    shareDraftByAsset[num] !== undefined
                                        ? shareDraftByAsset[num]
                                        : sh.toFixed(2);
                                const hCur = livePortfolio.numShares[idx];
                                const holdingsInputStr =
                                    holdingsDraftByAsset[num] !== undefined
                                        ? holdingsDraftByAsset[num]
                                        : String(hCur.toFixed(2));

                                return (
                                    <tr key={num}>
                                        <td>
                                            <span style={{ color: option.color, fontWeight: 'bold' }}>
                                                {option.label}
                                            </span>
                                        </td>
                                        <td id={priceCellId}>{formatNumber2(priceLeft)}</td>
                                        <td>{formatNumber2(option.numShares)}</td>
                                        <td>{formatNumber2(valueLeft)}</td>
                                        <td>{formatNumber2(shareLeft)}</td>
                                        <td> </td>
                                        <td>
                                            {isAdvisor ? (
                                                <span>{holdingsInputStr}</span>
                                            ) : (
                                                <div className="input-group input-group-sm justify-content-center inv-share-input-group">
                                                    <button
                                                        type="button"
                                                        className="btn btn-outline-secondary"
                                                        name={'investmentOption' + num + 'HoldingsButtonMinus'}
                                                        disabled={!canEdit}
                                                        onClick={() => changeHoldings(num, -1)}
                                                    >
                                                        −
                                                    </button>
                                                    <input
                                                        id={'newH' + num}
                                                        name={'investmentOption' + num + 'Holdings'}
                                                        type="number"
                                                        min={0}
                                                        //className="form-control text-center"
                                                        className="form-control text-center inv-num-input"
                                                        step="any"
                                                        style={INV_INPUT_STYLE}
                                                        value={holdingsInputStr}
                                                        disabled={!canEdit}
                                                        onFocus={() => {
                                                            delete lastLiveSentHoldingsRef.current[num];
                                                            setHoldingsDraftByAsset((prev) => ({
                                                                ...prev,
                                                                [num]: hCur.toFixed(2),
                                                            }));
                                                        }}
                                                        onChange={(e) => {
                                                            const raw = e.target.value;
                                                            setHoldingsDraftByAsset((prev) => ({
                                                                ...prev,
                                                                [num]: raw,
                                                            }));
                                                            debouncedSetHoldingsInput(num, raw);
                                                        }}
                                                        onBlur={(e) => {
                                                            const raw = e.target.value;
                                                            const timers = holdingsTimersRef.current;
                                                            const hadPending = !!timers[num];
                                                            if (hadPending) {
                                                                clearTimeout(timers[num]);
                                                                delete timers[num];
                                                                flushSetHoldingsInput(num, raw);
                                                            }
                                                            setHoldingsDraftByAsset((prev) => {
                                                                const next = { ...prev };
                                                                delete next[num];
                                                                return next;
                                                            });
                                                        }}
                                                    />
                                                    <button
                                                        type="button"
                                                        className="btn btn-outline-secondary"
                                                        name={'investmentOption' + num + 'HoldingsButtonPlus'}
                                                        disabled={!canEdit}
                                                        onClick={() => changeHoldings(num, 1)}
                                                    >
                                                        +
                                                    </button>
                                                </div>
                                            )}
                                        </td>
                                        <td id={'newVal' + num + 'Cell'}>
                                            <span id={'newVal' + num}>{formatNumber2(pv)}</span>
                                        </td>
                                        <td id={'newShare' + num + 'Cell'}>
                                            <div className="input-group input-group-sm justify-content-center inv-share-input-group">
                                                <button
                                                    type="button"
                                                    className="btn btn-outline-secondary"
                                                    name={'investmentOption' + num + 'ShareButtonMinus'}
                                                    disabled={!canEdit}
                                                    onClick={() => changeShares(num, -1)}
                                                >
                                                    −
                                                </button>
                                                <input
                                                    id={'newS' + num}
                                                    name={'investmentOption' + num + 'ShareAdj'}
                                                    type="number"
                                                    min={0}
                                                    max={100}
                                                    step="any"
                                                    //className="form-control text-center"
                                                    className="form-control text-center inv-num-input"
                                                    style={INV_INPUT_STYLE}
                                                    value={shareInputStr}
                                                    disabled={!canEdit}
                                                    onFocus={() => {
                                                        delete lastLiveSentShareRef.current[num];
                                                        setShareDraftByAsset((prev) => ({
                                                            ...prev,
                                                            [num]: sh.toFixed(2),
                                                        }));
                                                    }}
                                                    onChange={(e) => {
                                                        const raw = e.target.value;
                                                        setShareDraftByAsset((prev) => ({
                                                            ...prev,
                                                            [num]: raw,
                                                        }));
                                                        debouncedSetSharesInput(num, raw);
                                                    }}
                                                    onBlur={(e) => {
                                                        const raw = e.target.value;
                                                        const timers = shareTimersRef.current;
                                                        const hadPending = !!timers[num];
                                                        if (hadPending) {
                                                            clearTimeout(timers[num]);
                                                            delete timers[num];
                                                            flushSetSharesInput(num, raw);
                                                        }
                                                        setShareDraftByAsset((prev) => {
                                                            const next = { ...prev };
                                                            delete next[num];
                                                            return next;
                                                        });
                                                    }}
                                                />
                                                <button
                                                    type="button"
                                                    className="btn btn-outline-secondary"
                                                    name={'investmentOption' + num + 'ShareButtonPlus'}
                                                    disabled={!canEdit}
                                                    onClick={() => changeShares(num, 1)}
                                                >
                                                    +
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                            <tr key="risk-free">
                                <td>
                                    <span style={{ color: riskFreeAsset.color, fontWeight: 'bold' }}>
                                        {riskFreeAsset.label}
                                    </span>
                                </td>
                                <td>-</td>
                                <td>-</td>
                                <td>
                                    {formatNumber2(
                                        pageStatus === 'Old' ? riskFreeAsset.currentValue : riskFreeAsset.newValue,
                                    )}
                                </td>
                                <td>
                                    {formatNumber2(
                                        pageStatus === 'Old' ? riskFreeAsset.oldWealthShare : riskFreeAsset.newWealthShare,
                                    )}
                                </td>
                                <td> </td>
                                <td>-</td>
                                <td>
                                    <span id="riskFreeNewValue">{formatNumber2(livePortfolio.dollarHoldings[5])}</span>
                                </td>
                                <td>
                                    <span id="riskFreeNewShare">{formatNumber2(livePortfolio.allocation[5])}</span>
                                </td>
                            </tr>
                            <tr
                                key="total"
                                style={{ borderTop: '2px solid #bbb', fontWeight: 'bold' }}
                            >
                                <td>Total</td>
                                <td> </td>
                                <td> </td>
                                <td id="totalCurVal">{formatNumber2(valueTotalLeft)}</td>
                                <td>100.00</td>
                                <td> </td>
                                <td />
                                <td id="totalNewVal">{formatNumber2(livePortfolio.dollarHoldings.reduce((a, b) => a + Number(b), 0))}</td>
                                <td id="totalNewShare">{livePortfolio.allocation.reduce((a, b) => a + Number(b), 0) > 0 ? '100.00' : '—'}</td>
                            </tr>
                        </tbody>
                    </table>
                    </div>
                </div>
            </div>
        </div>
    );
}

function InvModuleApp() {
    const [pageStatus, setPageStatus] = React.useState('Old');
    const phase = js_vars.currentState;

    React.useEffect(() => {
        window.invModuleSetPageStatus = setPageStatus;
        return () => delete window.invModuleSetPageStatus;
    }, []);

    return <InvModule pageStatus={pageStatus} phase={phase} />;
}

// Button change functions
function changeShares ( num, dir ) {
    liveSend({type: 'changeShares', asset: num, direction: dir});
}

function changeHoldings ( num, dir ) {
    liveSend({type: 'changeHoldings', asset: num, direction: dir});
}

function setShares ( num, targetShare ) {
    liveSend({type: 'setShares', asset: num, targetShare: targetShare});
}

function sendHoldingsLive ( num, targetHoldings ) {
    liveSend({type: 'setHoldings', asset: num, targetHoldings: targetHoldings});
}


// Helper functions
function formatNumber2(val) {
    if (val === '-' || val === '—') return val;
    const n = Number(val);
    if (Number.isNaN(n)) return String(val);
    return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatNumber1(val) {
    if (val === '-' || val === '—') return val;
    const n = Number(val);
    if (Number.isNaN(n)) return String(val);
    return n.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

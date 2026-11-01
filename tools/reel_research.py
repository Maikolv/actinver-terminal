"""Offline feature research from the TradingView reel. No network or order API."""
from pathlib import Path
import argparse
import json
import math
import os

os.environ.setdefault('SMC_CREDIT', '0')
import pandas as pd
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.volatility import AverageTrueRange
from smartmoneyconcepts import smc


def validate(frame):
    frame = frame.copy()
    required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    if not set(required).issubset(frame.columns):
        raise ValueError('Required columns: ' + ', '.join(required))
    frame = frame[required]
    frame['timestamp'] = pd.to_datetime(frame.timestamp, utc=True, errors='raise')
    if frame.timestamp.isna().any() or frame.timestamp.duplicated().any():
        raise ValueError('Missing or duplicate timestamps')
    frame = frame.sort_values('timestamp').reset_index(drop=True)
    for col in required[1:]:
        frame[col] = pd.to_numeric(frame[col], errors='raise')
        if not frame[col].map(math.isfinite).all():
            raise ValueError('Non-finite ' + col)
    if len(frame) < 35:
        raise ValueError('At least 35 closed bars required')
    if (frame[['open','high','low','close']] <= 0).any().any() or (frame.volume < 0).any():
        raise ValueError('Invalid price or volume')
    if (frame.high < frame[['open','close','low']].max(axis=1)).any() or (frame.low > frame[['open','close','high']].min(axis=1)).any():
        raise ValueError('Invalid OHLC range')
    return frame


def features(frame):
    frame = validate(frame)
    result = frame.copy()
    result['sma20'] = SMAIndicator(frame.close, window=20, fillna=False).sma_indicator()
    result['ema20'] = EMAIndicator(frame.close, window=20, fillna=False).ema_indicator()
    result['macd_hist'] = MACD(frame.close, fillna=False).macd_diff()
    result['atr14'] = AverageTrueRange(frame.high, frame.low, frame.close, window=14, fillna=False).average_true_range()
    result.loc[:12, 'atr14'] = float('nan')
    # The package labels a gap on its center bar using shift(-1).
    # Expose it only when the third bar closes; mitigation uses future data and is excluded.
    gaps = smc.fvg(frame, join_consecutive=False)[['FVG','Top','Bottom']].shift(1)
    spacing = frame.timestamp.diff()
    interval = spacing.dropna().mode().iloc[0]
    contiguous = (spacing == interval) & (spacing.shift(1) == interval)
    gaps.loc[~contiguous, :] = float('nan')
    result[['fvg_confirmed','fvg_top','fvg_bottom']] = gaps.to_numpy()
    return result


def read_input(path):
    if path.suffix.lower() == '.csv':
        return pd.read_csv(path), 'CSV del usuario; procedencia por verificar'
    obj = json.loads(path.read_text(encoding='utf-8-sig'))
    frame = pd.DataFrame(obj['barras']).rename(columns=dict(inicio='timestamp', apertura='open',maximo='high',minimo='low',cierre='close',volumen='volume'))
    return frame, obj.get('uso', 'Procedencia no especificada')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    frame, source = read_input(args.input)
    result = features(frame)
    args.output.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output/'features.csv', index=False)
    summary = dict(bars=len(result), source=source, input=str(args.input.resolve()),
        start=result.timestamp.iloc[0].isoformat(),end=result.timestamp.iloc[-1].isoformat(),
        fvg_confirmed=int(result.fvg_confirmed.notna().sum()),
        purpose='OFFLINE FEATURE RESEARCH; NOT A STRATEGY OR CURRENT SIGNAL',
        orders_enabled=False, profitability_tested=False,
        warmup='SMA/EMA20, MACD12/26/9, ATR14; undefined values are not filled',
        caveat='FVG excluded across missing bars using the modal interval; no exchange session calendar applied. No aggressor delta inferred.')
    (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=True))


if __name__ == '__main__':
    main()

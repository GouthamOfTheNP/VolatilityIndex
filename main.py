import altair as alt
import pandas as pd
import pandas_ta as ta
import streamlit as st
import yfinance as yf

st.set_page_config(layout="wide", page_title="VIX 10", page_icon=":chart_with_upwards_trend:")
st.title("Volatility Index")

ticker = st.text_input("Enter Ticker Symbol", value="NVDA", max_chars=10).upper()


def map_to_scale(value, max_threshold):
	score = (value / max_threshold) * 10
	return min(score, 10.0)


if ticker:
	df = yf.download(ticker, period="1y", multi_level_index=False)

	if not df.empty and len(df) > 50:
		df['Daily_Return'] = df['Close'].pct_change()
		df['Abs_Daily_Move'] = df['Daily_Return'].abs()
		df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
		df['ATR_Pct'] = df['ATR'] / df['Close']
		last_row = df.iloc[-1]
		VOLATILITY_CAP_PCT = 0.06

		score_abs_daily = map_to_scale(last_row['Abs_Daily_Move'], VOLATILITY_CAP_PCT)
		score_abs_atr = map_to_scale(last_row['ATR_Pct'], VOLATILITY_CAP_PCT)
		daily_rank = df['Abs_Daily_Move'].rank(pct=True).iloc[-1] * 10

		final_vix = (score_abs_daily * 0.50) + (score_abs_atr * 0.30) + (daily_rank * 0.20)
		col1, col2 = st.columns([1, 2])

		with col1:
			st.metric(label="VIX Score (0-10)", value=f"{final_vix:.2f}")
			if final_vix > 8.0:
				st.error(f"High Volatility ({last_row['Abs_Daily_Move']:.2%} Move)")
			elif final_vix < 3.0:
				st.success(f"Low Volatility ({last_row['Abs_Daily_Move']:.2%} Move)")
			else:
				st.info(f"Moderate Volatility ({last_row['Abs_Daily_Move']:.2%} Move)")

			st.write("---")
			st.write("**Why this score?**")

			st.metric("1. Absolute Daily Move (50%)",
			          f"{score_abs_daily:.2f}/10",
			          help=f"Today's move was {last_row['Abs_Daily_Move']:.2%}. A 6% move scores 10.")

			st.metric("2. Absolute Range/ATR (30%)",
			          f"{score_abs_atr:.2f}/10",
			          help=f"This stock usually swings {last_row['ATR_Pct']:.2%} per day.")

			st.metric("3. Relative Rank (20%)",
			          f"{daily_rank:.2f}/10",
			          help="How today compares to the stock's own past year.")

		with col2:
			plot_df = df.iloc[-100:].reset_index()
			bar_chart = alt.Chart(plot_df).mark_bar().encode(
				x=alt.X("Date:T", title=None),
				y=alt.Y("Abs_Daily_Move:Q", title="Daily Movement %", axis=alt.Axis(format='%')),
				color=alt.condition(
					alt.datum.Daily_Return > 0,
					alt.value("#26a69a"),
					alt.value("#ef5350")
				),
				tooltip=["Date:T", alt.Tooltip("Daily_Return", format=".2%")]
			).properties(title="Daily % Moves (Absolute Scale)", height=300)

			rule = alt.Chart(pd.DataFrame({'y': [VOLATILITY_CAP_PCT]})).mark_rule(color='orange', strokeDash=[5, 5]).encode(y='y')
			text = alt.Chart(pd.DataFrame({'y': [VOLATILITY_CAP_PCT], 'label': ['Max Vol Threshold (6%)']})).mark_text(
				align='left', dx=5, dy=-5, color='orange'
			).encode(y='y', text='label')

			st.altair_chart(bar_chart + rule + text)

			rsi_series = ta.rsi(df["Close"]).iloc[-252:]
			rsi_df = rsi_series.to_frame(name="RSI").reset_index()

			rsi_chart = alt.Chart(rsi_df).mark_line().encode(
				x=alt.X("Date:T", title=None),
				y=alt.Y("RSI:Q", scale=alt.Scale(domain=[0, 100]))
			).properties(title="RSI (Momentum)", height=200)
			rsi_lines = (alt.Chart(pd.DataFrame({'y': [30, 70]})).mark_rule(strokeDash=[5, 5], color='gray').encode(y='y'))

			st.altair_chart(rsi_chart + rsi_lines)

			atr_line = alt.Chart(plot_df).mark_area(
				line={'color': 'gray'},
				color=alt.Gradient(
					gradient='linear',
					stops=[alt.GradientStop(offset=0, color='white'),
					       alt.GradientStop(offset=1, color='gray')],
					x1=1, x2=1, y1=1, y2=0
				)
			).encode(
				x=alt.X("Date:T", title="Date"),
				y=alt.Y("ATR:Q", title="ATR (Volatility)")
			).properties(height=200)

			st.altair_chart(atr_line)
	else:
		st.error("Not enough data. Please check ticker.")

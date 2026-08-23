import streamlit as st
import yfinance as yf
import numpy as np

st.set_page_config(page_title="Scanner de Verticals", layout="centered")

st.title("⚡ Dynamic Vertical Spread Matrix")
st.caption("Análisis macro + Beta/Correlación + Selección de Strikes")

ticker_symbol = st.text_input("Ticker de la Acción:", value="AAPL").upper()
strike_width = st.number_input("Ancho deseado del Spread ($):", value=5.0, step=1.0)

if st.button("🔍 Analizar Mercado y Generar Estrategia", use_container_width=True):
    with st.spinner("Procesando datos de SPY y la acción..."):
        try:
            data = yf.download([ticker_symbol, "SPY"], period="6m", progress=False)['Close']
            returns = data.pct_change().dropna()

            stock_ret = returns[ticker_symbol]
            spy_ret = returns["SPY"]

            spy_hist = yf.Ticker("SPY").history(period="3m")
            spy_price = spy_hist['Close'].iloc[-1]
            spy_sma50 = spy_hist['Close'].rolling(50).mean().iloc[-1]
            market_trend = "ALCISTA" if spy_price > spy_sma50 else "BAJISTA"

            stock_hist = yf.Ticker(ticker_symbol).history(period="3m")
            stock_price = stock_hist['Close'].iloc[-1]
            stock_sma50 = stock_hist['Close'].rolling(50).mean().iloc[-1]
            stock_trend = "ALCISTA" if stock_price > stock_sma50 else "BAJISTA"

            covarianza = np.cov(stock_ret, spy_ret)[0][1]
            varianza_spy = np.var(spy_ret)
            beta = covarianza / varianza_spy
            correlacion = stock_ret.corr(spy_ret)

            ticker_obj = yf.Ticker(ticker_symbol)
            expirations = ticker_obj.options
            
            if expirations:
                exp_target = expirations[min(2, len(expirations)-1)]
                opt_chain = ticker_obj.option_chain(exp_target)
                calls = opt_chain.calls
                iv_mean = calls['impliedVolatility'].mean() * 100
                iv_high = iv_mean > 35.0 
            else:
                iv_mean = 0.0
                iv_high = False

            if correlacion > 0.5:
                sesgo_final = market_trend if market_trend == stock_trend else stock_trend
            else:
                sesgo_final = stock_trend

            if sesgo_final == "ALCISTA":
                if not iv_high:
                    estrategia = "Bull Call Spread"
                    tipo = "Débito"
                    regla = f"Pagar máximo el 50% del ancho (≤ ${strike_width * 0.5:.2f})"
                    deltas = "Comprar Delta ~0.60 (ITM/ATM) | Vender Delta ~0.30 (OTM)"
                else:
                    estrategia = "Bull Put Spread"
                    tipo = "Crédito"
                    regla = f"Ingresar al menos 1/3 del ancho (≥ ${strike_width * 0.33:.2f})"
                    deltas = "Vender Delta ~0.20-0.30 (Soporte OTM) | Comprar Delta ~0.10 (Protección)"
            else:
                if not iv_high:
                    estrategia = "Bear Put Spread"
                    tipo = "Débito"
                    regla = f"Pagar máximo el 50% del ancho (≤ ${strike_width * 0.5:.2f})"
                    deltas = "Comprar Delta ~0.60 (ITM/ATM) | Vender Delta ~0.30 (OTM)"
                else:
                    estrategia = "Bear Call Spread"
                    tipo = "Crédito"
                    regla = f"Ingresar al menos 1/3 del ancho (≥ ${strike_width * 0.33:.2f})"
                    deltas = "Vender Delta ~0.20-0.30 (Resistencia OTM) | Comprar Delta ~0.10 (Protección)"

            st.markdown("---")
            st.metric("Estrategia Sugerida", estrategia, delta=f"Tipo: {tipo}")
            
            col1, col2 = st.columns(2)
            col1.metric("Tendencia SPY", market_trend)
            col1.metric("Beta vs SPY", f"{beta:.2f}")
            
            col2.metric(f"Tendencia {ticker_symbol}", stock_trend)
            col2.metric("Correlación", f"{correlacion:.2f}")

            st.subheader("📋 Parámetros de Ejecución")
            st.write(f"• **IV Media:** `{iv_mean:.1f}%` ({'IV Alta: Vender Prima' if iv_high else 'IV Baja: Comprar Prima'})")
            st.write(f"• **Deltas:** {deltas}")
            st.write(f"• **Regla Financiera:** {regla}")

        except Exception as e:
            st.error(f"Error procesando el ticker '{ticker_symbol}'. Verifique la ortografía.")

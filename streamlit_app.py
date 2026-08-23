import streamlit as st
import yfinance as yf
import numpy as np

st.set_page_config(page_title="Scanner de Verticals", layout="centered")

st.title("⚡ Dynamic Vertical Spread Matrix")
st.caption("Análisis macro + Beta/Correlación + Selección de Strikes")

ticker_symbol = st.text_input("Ticker de la Acción:", value="TSLA").upper().strip()
strike_width = st.number_input("Ancho deseado del Spread ($):", value=5.0, step=1.0)

if st.button("🔍 Analizar Mercado y Generar Estrategia", use_container_width=True):
    with st.spinner("Procesando datos de SPY y la acción..."):
        try:
            # Descarga individual para evitar bloqueos de la API
            stock_obj = yf.Ticker(ticker_symbol)
            spy_obj = yf.Ticker("SPY")

            stock_hist = stock_obj.history(period="6m")
            spy_hist = spy_obj.history(period="6m")

            if stock_hist.empty or spy_hist.empty:
                st.error(f"No se encontraron datos para el ticker '{ticker_symbol}'.")
            else:
                stock_close = stock_hist['Close']
                spy_close = spy_hist['Close']

                # Tendencia respecto a la SMA 50
                stock_price = stock_close.iloc[-1]
                stock_sma50 = stock_close.rolling(50).mean().iloc[-1]
                stock_trend = "ALCISTA" if stock_price > stock_sma50 else "BAJISTA"

                spy_price = spy_close.iloc[-1]
                spy_sma50 = spy_close.rolling(50).mean().iloc[-1]
                market_trend = "ALCISTA" if spy_price > spy_sma50 else "BAJISTA"

                # Cálculo de Beta y Correlación
                stock_ret = stock_close.pct_change().dropna()
                spy_ret = spy_close.pct_change().dropna()
                
                # Sincronizar fechas
                combined = pd.concat([stock_ret, spy_ret], axis=1, keys=['stock', 'spy']).dropna()
                covarianza = np.cov(combined['stock'], combined['spy'])[0][1]
                varianza_spy = np.var(combined['spy'])
                beta = covarianza / varianza_spy if varianza_spy != 0 else 1.0
                correlacion = combined['stock'].corr(combined['spy'])

                # Datos de Opciones e Implied Volatility (IV)
                expirations = stock_obj.options
                if expirations:
                    exp_target = expirations[min(2, len(expirations)-1)]
                    opt_chain = stock_obj.option_chain(exp_target)
                    calls = opt_chain.calls
                    iv_mean = calls['impliedVolatility'].mean() * 100
                    iv_high = iv_mean > 45.0  # Umbral de IV alta para alta volatilidad como TSLA
                else:
                    iv_mean = 0.0
                    iv_high = False

                # Matriz de decisión
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

                # Despliegue de resultados
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
            st.error(f"Error procesando los datos: {e}")


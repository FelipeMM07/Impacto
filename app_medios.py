import pandas as pd
import pulp
import streamlit as st

st.set_page_config(page_title="Optimización de medios", page_icon="📢", layout="wide")
st.title("📢 Maximizar impacto publicitario")
st.caption("Programación lineal con PuLP: elige cuánto invertir en cada medio para maximizar el impacto sin superar el presupuesto.")

# ---------------- Parámetros editables ----------------
datos_iniciales = pd.DataFrame(
    {
        "Medio": ["TV", "Radio", "Redes Sociales", "Prensa"],
        "Costo": [8.0, 3.0, 4.0, 2.0],
        "Impacto": [14.0, 5.0, 7.0, 3.0],
    }
)

with st.sidebar:
    st.header("⚙️ Parámetros")
    presupuesto = st.number_input("Presupuesto disponible", min_value=0.0, value=9.0, step=1.0)
    tipo = st.radio(
        "Tipo de variable de decisión",
        ["Binaria (usar o no el medio)", "Entera (nº de unidades)", "Continua"],
        index=0,
    )
    max_unidades = None
    if tipo.startswith("Entera"):
        max_unidades = st.number_input("Máx. unidades por medio (0 = sin límite)", min_value=0, value=0, step=1)

st.subheader("Costo e impacto por medio")
st.write("Edita los valores directamente en la tabla (también puedes agregar o quitar filas).")
df = st.data_editor(datos_iniciales, num_rows="dynamic", use_container_width=True, key="editor")

# ---------------- Resolución ----------------
def resolver(df, presupuesto, tipo, max_unidades):
    df = df.dropna().reset_index(drop=True)
    df = df[df["Medio"].astype(str).str.strip() != ""].reset_index(drop=True)
    if df.empty:
        return None, None, None

    prob = pulp.LpProblem("Maximizar_Impacto", pulp.LpMaximize)

    nombres = [f"x_{i}" for i in range(len(df))]
    if tipo.startswith("Binaria"):
        x = [pulp.LpVariable(n, cat="Binary") for n in nombres]
    elif tipo.startswith("Entera"):
        up = max_unidades if max_unidades else None
        x = [pulp.LpVariable(n, lowBound=0, upBound=up, cat="Integer") for n in nombres]
    else:
        x = [pulp.LpVariable(n, lowBound=0, cat="Continuous") for n in nombres]

    prob += pulp.lpSum(df.loc[i, "Impacto"] * x[i] for i in range(len(df))), "Impacto_total"
    prob += pulp.lpSum(df.loc[i, "Costo"] * x[i] for i in range(len(df))) <= presupuesto, "Presupuesto"

    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    res = df.copy()
    res["Cantidad"] = [v.value() if v.value() is not None else 0 for v in x]
    res["Costo total"] = res["Cantidad"] * res["Costo"]
    res["Impacto total"] = res["Cantidad"] * res["Impacto"]
    return prob, res, pulp.LpStatus[prob.status]


if st.button("🚀 Resolver", type="primary"):
    prob, res, estado = resolver(df, presupuesto, tipo, max_unidades)

    if prob is None:
        st.error("Agrega al menos un medio con datos válidos.")
    else:
        st.subheader("Resultado")
        if estado != "Optimal":
            st.error(f"Estado del solver: {estado}")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Impacto total", f"{pulp.value(prob.objective):,.2f}")
            c2.metric("Costo utilizado", f"{res['Costo total'].sum():,.2f}")
            c3.metric("Presupuesto sobrante", f"{presupuesto - res['Costo total'].sum():,.2f}")

            st.dataframe(res.round(4), use_container_width=True)
            st.bar_chart(res.set_index("Medio")["Impacto total"])

            with st.expander("Ver formulación del modelo"):
                st.code(str(prob), language="text")
else:
    st.info("Ajusta los parámetros y pulsa **Resolver**.")

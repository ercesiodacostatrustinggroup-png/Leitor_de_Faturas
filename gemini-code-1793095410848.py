import streamlit as st
import pandas as pd
from PIL import Image
import os
import io
import json
import base64
from openai import OpenAI

# Configuração da página
st.set_page_config(
    page_title="Leitor de Faturas IA - Grupo TrustinG", 
    page_icon="📄", 
    layout="wide"
)

# Estilização visual (Grupo TrustinG)
st.markdown("""
    <style>
    .main-header { font-size: 26px; font-weight: bold; color: #D96B27; }
    .sub-header { font-size: 16px; color: #555555; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📄 Leitor Automático de Faturas (IA)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Grupo TrustinG - Processamento Automático de Imagens para Excel</div>', unsafe_allow_html=True)

# -------------------------------------------------------------
# CONFIGURAÇÃO DA CHAVE API DA OPENAI
# -------------------------------------------------------------
api_key = st.sidebar.text_input("Chave API da OpenAI (sk-...)", type="password")

if not api_key:
    st.sidebar.warning("Por favor, insira a sua API Key da OpenAI para ativar a leitura automática por IA.")

EXCEL_FILE = "faturas_grupo_trusting.xlsx"
COLUMNAS = [
    "Data de Registo", "Fornecedor", "NUIT", "Nº da Fatura", 
    "Data da Fatura", "Categoria", "Projeto/Cliente", 
    "Valor Base (MT)", "IVA (MT)", "Valor Total (MT)", "Observações"
]

if os.path.exists(EXCEL_FILE):
    df_existing = pd.read_excel(EXCEL_FILE)
else:
    df_existing = pd.DataFrame(columns=COLUMNAS)

# -------------------------------------------------------------
# FUNÇÃO DE EXTRAÇÃO DE DADOS VIA VISION AI
# -------------------------------------------------------------
def extrair_dados_fatura(image_bytes, client):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    prompt = """
    Analisa esta imagem de fatura/recibo e extrai os seguintes dados no formato JSON estrito:
    {
      "fornecedor": "Nome da Empresa ou Fornecedor",
      "nuit": "Número NUIT/NIF do Fornecedor",
      "num_fatura": "Número da Fatura/Recibo",
      "data_fatura": "YYYY-MM-DD",
      "categoria": "Escolhe a mais adequada entre: [Material de Limpeza e Higiene, Manutenção (Elétrica / Ar Condicionado / Piscinas), Peças e Oficinas / Viaturas, Combustível, Material de Jardinagem, Serviços Subcontratados, Outros]",
      "valor_base": 0.00 (número decimal),
      "iva": 0.00 (número decimal),
      "valor_total": 0.00 (número decimal),
      "observacoes": "Resumo breve dos itens ou descrição do serviço"
    }
    Se algum campo não for visível ou legível, deixa em branco ("") ou 0.00 para valores numéricos. Responde APENAS com o objeto JSON.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }
        ],
        max_tokens=500
    )
    
    content = response.choices[0].message.content.strip()
    if content.startswith("```json"):
        content = content.replace("```json", "").replace("```", "").strip()
    
    return json.loads(content)

# -------------------------------------------------------------
# PAINEL PRINCIPAL
# -------------------------------------------------------------
col_upload, col_data = st.columns([1, 1])

dados_iniciais = {
    "fornecedor": "", "nuit": "", "num_fatura": "", 
    "data_fatura": "", "categoria": "Outros", 
    "valor_base": 0.0, "iva": 0.0, "valor_total": 0.0, "observacoes": ""
}

with col_upload:
    st.subheader("1. Carregar Foto da Fatura")
    uploaded_file = st.file_uploader("Selecione a foto ou scan (JPG, PNG, JPEG)", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        image_bytes = uploaded_file.read()
        image = Image.open(io.BytesIO(image_bytes))
        st.image(image, caption="Imagem da Fatura", use_column_width=True)
        
        if api_key and st.button("✨ Ler Fatura com Inteligência Artificial"):
            with st.spinner("A analisar a fatura com Visão Computacional..."):
                try:
                    client = OpenAI(api_key=api_key)
                    dados_extraidos = extrair_dados_fatura(image_bytes, client)
                    st.session_state["dados_fatura"] = dados_extraidos
                    st.success("Leitura concluída com sucesso! Verifique os dados ao lado.")
                except Exception as e:
                    st.error(f"Erro ao processar imagem: {e}")

if "dados_fatura" in st.session_state:
    dados_iniciais = st.session_state["dados_fatura"]

with col_data:
    st.subheader("2. Validação e Lançamento no Excel")
    
    with st.form("form_fatura"):
        fornecedor = st.text_input("Fornecedor / Empresa", value=dados_iniciais.get("fornecedor", ""))
        nuit = st.text_input("NUIT do Fornecedor", value=dados_iniciais.get("nuit", ""))
        num_fatura = st.text_input("Número da Fatura", value=dados_iniciais.get("num_fatura", ""))
        
        data_val = dados_iniciais.get("data_fatura", "")
        data_fatura = st.text_input("Data de Emissão (AAAA-MM-DD)", value=data_val)
        
        categorias_lista = [
            "Material de Limpeza e Higiene", 
            "Manutenção (Elétrica / Ar Condicionado / Piscinas)", 
            "Peças e Oficinas / Viaturas", 
            "Combustível", 
            "Material de Jardinagem", 
            "Serviços Subcontratados",
            "Outros"
        ]
        
        cat_index = 6
        if dados_iniciais.get("categoria") in categorias_lista:
            cat_index = categorias_lista.index(dados_iniciais.get("categoria"))
            
        categoria = st.selectbox("Categoria de Despesa", categorias_lista, index=cat_index)
        projeto_cliente = st.text_input("Projeto / Cliente Destino", value="Geral / Interno")
        
        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1:
            valor_base = st.number_input("Valor Base (MT)", value=float(dados_iniciais.get("valor_base", 0.0)), format="%.2f")
        with col_v2:
            iva = st.number_input("IVA (MT)", value=float(dados_iniciais.get("iva", 0.0)), format="%.2f")
        with col_v3:
            valor_total = st.number_input("Valor Total (MT)", value=float(dados_iniciais.get("valor_total", 0.0)), format="%.2f")
            
        obs = st.text_area("Descrição / Observações", value=dados_iniciais.get("observacoes", ""))
        
        btn_salvar = st.form_submit_button("💾 Confirmar e Lançar no Excel")
        
        if btn_salvar:
            novo_registo = {
                "Data de Registo": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                "Fornecedor": fornecedor,
                "NUIT": nuit,
                "Nº da Fatura": num_fatura,
                "Data da Fatura": data_fatura,
                "Categoria": categoria,
                "Projeto/Cliente": projeto_cliente,
                "Valor Base (MT)": valor_base,
                "IVA (MT)": iva,
                "Valor Total (MT)": valor_total,
                "Observações": obs
            }
            
            df_updated = pd.concat([df_existing, pd.DataFrame([novo_registo])], ignore_index=True)
            df_updated.to_excel(EXCEL_FILE, index=False)
            st.success("Fatura lançada no Excel com sucesso!")
            if "dados_fatura" in st.session_state:
                del st.session_state["dados_fatura"]
            st.rerun()

# -------------------------------------------------------------
# HISTÓRICO E EXPORTAÇÃO
# -------------------------------------------------------------
st.divider()
st.subheader("📊 Histórico de Faturas Registadas")

if not df_existing.empty:
    st.dataframe(df_existing, use_container_width=True)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_existing.to_excel(writer, index=False)
        
    st.download_button(
        label="📥 Descarregar Folha de Cálculo Excel (.xlsx)",
        data=buffer.getvalue(),
        file_name="faturas_grupo_trusting.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Ainda não existem faturas registradas na base de dados.")
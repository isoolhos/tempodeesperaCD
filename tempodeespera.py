import cx_Oracle
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import time

# Configuração do título do Streamlit
st.title("📊 Monitoramento | Tempo de Espera no CD")

# Criar espaços para exibir os gráficos no Streamlit
dados_placeholder = st.empty()
grafico_terreo_placeholder = st.empty()
grafico_piso1_placeholder = st.empty()
grafico_comparacao_placeholder = st.empty()

# config conexão 
usuario = "tasy"
senha = "aloisk"
host = "192.168.120.102"
porta = "1521"
service_name = "tasy.subnetprivate.vcn01.oraclevcn.com"

# Função para obter os dados do banco de dados
def obter_dados():
    try:
        # Criar conexão com o Oracle
        dsn_tns = cx_Oracle.makedsn(host, porta, service_name=service_name)
        conexao = cx_Oracle.connect(user=usuario, password=senha, dsn=dsn_tns)
        cursor = conexao.cursor()

        # Consulta SQL
        query = """
        SELECT status, agenda, nomepac, 
               to_char(HORA_INI,'hh24:mi:ss') as INI_CD,
               round(((sysdate - HORA_INI)* 1440),2) as tempocd     
        FROM (
            SELECT substr(obter_descricao_padrao('STATUS_PACIENTE_AGENDA', 'DS_STATUS_PACIENTE', NR_SEQ_STATUS_PAC),1,100) as status,
                   obter_desc_agenda(cd_agenda) as agenda,
                   obter_nome_pf(cd_pessoa_fisica) as nomepac,
                   case 
                       when substr(obter_descricao_padrao('STATUS_PACIENTE_AGENDA', 'DS_STATUS_PACIENTE', NR_SEQ_STATUS_PAC),1,100) = ('CD Térreo')   
                       then (Select max(dt_historico) 
                             from agenda_paciente_hist b
                             where b.nr_seq_agenda = a.NR_SEQUENCIA
                             and ds_historico like '%para CD Térreo%')
                       else (Select max(dt_historico)
                             from agenda_paciente_hist b
                             where b.nr_seq_agenda = a.NR_SEQUENCIA
                             and ds_historico like '%para CD 1º Piso%')
                   end as HORA_INI
            FROM AGENDA_PACIENTE A
            WHERE TRUNC(HR_INICIO) = trunc(sysdate)
              AND substr(obter_descricao_padrao('STATUS_PACIENTE_AGENDA', 'DS_STATUS_PACIENTE', NR_SEQ_STATUS_PAC),1,100) 
                  IN ('CD Térreo', 'CD 1º Piso')
              and obter_desc_agenda(cd_agenda) not like '%Bloco%'
        )
        ORDER BY 1, 5 DESC
        """

        # Executar a consulta
        cursor.execute(query)

        # Obter os nomes das colunas
        colunas = [col[0] for col in cursor.description]

        # Obter os dados
        dados = cursor.fetchall()

        # Fechar conexão
        cursor.close()
        conexao.close()

        # Criar DataFrame manualmente
        df = pd.DataFrame(dados, columns=colunas)

        return df

    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro

# Atualizar os dados periodicamente
while True:
    df = obter_dados()  # Buscar os dados mais recentes do banco

    if df.empty:
        st.warning("⚠️ Nenhum dado encontrado para o período selecionado.")
    else:
        # Converter colunas para maiúsculas para evitar erros
        df.columns = df.columns.str.upper()

        # Exibir os dados como tabela no Streamlit
        dados_placeholder.write(df)

        # Remover valores nulos para evitar erros
        df = df.dropna(subset=['STATUS', 'NOMEPAC', 'TEMPOCD'])

        # Converter colunas para os tipos corretos
        df['STATUS'] = df['STATUS'].astype(str)
        df['NOMEPAC'] = df['NOMEPAC'].astype(str)
        df['TEMPOCD'] = df['TEMPOCD'].astype(float)

        # Separar os dados por setor
        df_terreo = df[df['STATUS'] == 'CD Térreo']
        df_piso1 = df[df['STATUS'] == 'CD 1º Piso']

        ### 📊 **Gráfico 1: Tempo de Espera - CD Térreo**
        fig_terreo, ax1 = plt.subplots(figsize=(4, 2))
        ax1.barh(df_terreo['NOMEPAC'], df_terreo['TEMPOCD'], color='lightblue')
        ax1.set_xlabel('Tempo no Setor (Minutos)')
        ax1.set_ylabel('Nome do Paciente')
        ax1.set_title('⏳ Tempo Médio de Espera - CD Térreo')
        ax1.invert_yaxis()
        ax1.grid(axis='x', linestyle='--', alpha=0.7)

        # Exibir valores dentro das barras
        for index, value in enumerate(df_terreo['TEMPOCD']):
            ax1.text(value + 1, index, str(value), va='center')

        grafico_terreo_placeholder.pyplot(fig_terreo)

        ### 📊 **Gráfico 2: Tempo de Espera - 1º Piso**
        fig_piso1, ax2 = plt.subplots(figsize=(4, 2))
        ax2.barh(df_piso1['NOMEPAC'], df_piso1['TEMPOCD'], color='salmon')
        ax2.set_xlabel('Tempo no Setor (Minutos)')
        ax2.set_ylabel('Nome do Paciente')
        ax2.set_title('⏳ Tempo Médio de Espera - 1º Piso')
        ax2.invert_yaxis()
        ax2.grid(axis='x', linestyle='--', alpha=0.7)

        for index, value in enumerate(df_piso1['TEMPOCD']):
            ax2.text(value + 1, index, str(value), va='center')

        grafico_piso1_placeholder.pyplot(fig_piso1)

        ### 📊 **Gráfico 3: Comparação de Pacientes nos Setores**
        num_pacientes_terreo = len(df_terreo)
        num_pacientes_piso1 = len(df_piso1)

        fig_comparacao, ax3 = plt.subplots(figsize=(4, 2))
        ax3.bar(['CD Térreo', '1º Piso'], [num_pacientes_terreo, num_pacientes_piso1], color=['lightblue', 'lightgreen'])
        ax3.set_ylabel('Número de Pacientes')
        ax3.set_title('📈 Comparação: Pacientes por Setor')

        for index, value in enumerate([num_pacientes_terreo, num_pacientes_piso1]):
            ax3.text(index, value + 0.5, str(value), ha='center')

        grafico_comparacao_placeholder.pyplot(fig_comparacao)

    # Atualizar a cada 30 segundos
    time.sleep(30)

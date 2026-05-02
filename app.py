import streamlit as st
import subprocess
import tempfile
import os
import pandas as pd
from Bio.Blast import NCBIXML

# ページ全体の設定
st.set_page_config(page_title="Hybrid QuickBLAST", layout="wide")

# ==========================================
# サイドバー：実行モードとパスの設定
# ==========================================
st.sidebar.title("⚙️ 実行設定")
exec_mode = st.sidebar.radio(
    "実行モードを選択してください",
    ("クラウド・お手軽モード (環境構築不要)", "ローカル・本格モード (自身のPCで実行)")
)

# モードに応じてBLASTのコマンドパスを辞書に格納して切り替える
cmds = {}
if exec_mode == "クラウド・お手軽モード (環境構築不要)":
    st.sidebar.info("💡 サーバー上のBLASTを使用します。小さなファイルや特化型DBの検索に適しています。")
    cmds = {
        "makeblastdb": "makeblastdb",
        "blastp": "blastp",
        "blastn": "blastn",
        "blastx": "blastx"
    }
else:
    st.sidebar.warning("⚠️ 自身のPCにNCBI BLAST+がインストールされている必要があります。")
    blast_bin_path = st.sidebar.text_input(
        "BLASTのbinフォルダのパスを指定してください", 
        r"C:\Program Files\NCBI\blast-2.16.0+\bin"
    )
    cmds = {
        "makeblastdb": os.path.join(blast_bin_path, "makeblastdb.exe"),
        "blastp": os.path.join(blast_bin_path, "blastp.exe"),
        "blastn": os.path.join(blast_bin_path, "blastn.exe"),
        "blastx": os.path.join(blast_bin_path, "blastx.exe")
    }

# メイン画面タイトル
st.title("🧬 Hybrid QuickBLAST")
st.write(f"現在のモード: **{exec_mode}**")

# 機能ごとにタブを分ける
tab1, tab2 = st.tabs(["🔍 BLAST検索", "📁 データベース作成 (初回のみ)"])

# ==========================================
# タブ2: データベース作成機能
# ==========================================
with tab2:
    st.header("ローカルデータベースの作成")
    st.write("検索対象にしたいFASTAファイルをアップロードして、専用のDBを作成します。")
    
    db_fasta = st.file_uploader("データベース用FASTAファイルをアップロード", type=["fasta", "fas", "txt"])
    db_type = st.selectbox("配列の種類", ["prot (アミノ酸配列)", "nucl (塩基配列)"])
    db_name = st.text_input("作成するデータベース名 (半角英数字)", "my_local_db")

    if st.button("🛠️ データベースを作成する", type="primary"):
        if db_fasta is not None:
            db_type_arg = "prot" if "prot" in db_type else "nucl"
            
            # アップロードされたファイルを一時保存
            fasta_path = f"{db_name}.fasta"
            with open(fasta_path, "wb") as f:
                f.write(db_fasta.getvalue())

            # makeblastdb コマンドの組み立てと実行
            cmd = [cmds["makeblastdb"], "-in", fasta_path, "-dbtype", db_type_arg, "-out", db_name]
            try:
                # 実行モード確認用（デバッグ用に出力）
                st.caption(f"実行コマンド: {' '.join(cmd)}")
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                st.success(f"✅ データベース '{db_name}' の作成が完了しました！検索タブに進んでください。")
            except subprocess.CalledProcessError as e:
                st.error("エラーが発生しました。パスの設定やファイルの中身を確認してください。")
                st.error(f"詳細エラー: {e.stderr}")
            except FileNotFoundError:
                st.error("指定されたパスに makeblastdb が見つかりません。サイドバーのパス設定を確認してください。")
        else:
            st.warning("FASTAファイルをアップロードしてください。")

# ==========================================
# タブ1: BLAST検索機能
# ==========================================
with tab1:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. 検索配列の入力")
        query_file = st.file_uploader("手元のFASTAファイルをドラッグ＆ドロップ", type=["fasta", "fas", "txt"])
        st.write("または")
        query_text = st.text_area("ここに直接配列をペースト (FASTA形式)", height=150)

    with col2:
        st.subheader("2. 検索オプション")
        program_display = st.selectbox("プログラム", ["blastp (タンパク質)", "blastn (塩基)", "blastx (塩基→タンパク質)"])
        program_key = program_display.split(" ")[0] # blastp などだけを抽出してキーにする
        target_db = st.text_input("検索先データベース名", "my_local_db")
        e_value = st.slider("E-value しきい値", min_value=0.0, max_value=10.0, value=1e-5, format="%e")

    # 検索実行ボタン
    if st.button("🚀 BLAST検索を実行", type="primary", use_container_width=True):
        if not query_file and not query_text.strip():
            st.warning("検索する配列を入力してください。")
        else:
            with st.spinner("BLAST検索を裏側で実行中..."):
                # 検索配列を一時ファイルとして保存
                with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".fasta", encoding="utf-8") as temp_query:
                    if query_file:
                        temp_query.write(query_file.getvalue().decode("utf-8"))
                    else:
                        temp_query.write(query_text)
                    query_path = temp_query.name

                xml_out = "blast_results.xml"
                
                # blast コマンドの組み立て
                cmd = [
                    cmds[program_key],
                    "-query", query_path,
                    "-db", target_db,
                    "-evalue", str(e_value),
                    "-outfmt", "5",  # Biopythonで解析しやすいXML形式で出力
                    "-out", xml_out
                ]

                try:
                    # 実行コマンド確認用
                    st.caption(f"実行コマンド: {' '.join(cmd)}")
                    subprocess.run(cmd, check=True, capture_output=True, text=True)

                    # Biopython で XML 結果をパース（解読）
                    records = NCBIXML.parse(open(xml_out))
                    results_list = []

                    for record in records:
                        for alignment in record.alignments:
                            for hsp in alignment.hsps:
                                results_list.append({
                                    "ターゲット配列": alignment.title[:80], # 長い名前はカット
                                    "Score": hsp.score,
                                    "E-value": hsp.expect,
                                    "Identity (%)": round((hsp.identities / hsp.align_length) * 100, 1)
                                })

                    # 結果の表示
                    st.divider()
                    st.subheader("📊 解析結果")
                    if results_list:
                        df = pd.DataFrame(results_list)
                        st.dataframe(df, use_container_width=True) # きれいな表で表示
                        
                        # スコアの可視化
                        st.caption("ヒットした配列のスコア比較")
                        st.bar_chart(df.set_index("ターゲット配列")["Score"])
                    else:
                        st.info("条件に一致する配列は見つかりませんでした。E-valueを調整してみてください。")

                except subprocess.CalledProcessError as e:
                    st.error("BLASTの実行に失敗しました。データベースが作成されているか、パスが正しいか確認してください。")
                    st.error(f"詳細エラー: {e.stderr}")
                except FileNotFoundError:
                    st.error(f"指定されたパスに {program_key} が見つかりません。サイドバーのパス設定を確認してください。")
                finally:
                    # ゴミ箱のお掃除（一時ファイルの削除）
                    if os.path.exists(query_path): os.remove(query_path)
                    if os.path.exists(xml_out): os.remove(xml_out)
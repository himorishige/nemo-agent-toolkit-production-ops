FROM nat-nim-handson:1.6.0

# annoy（NeMo Guardrails の依存）は ARM64 wheel が公開されておらず
# pip install 時にソースから C++ ビルドする。build-essential を入れて通す。
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    "nemoguardrails==0.21.0"

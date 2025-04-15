nuitka src/main.py \
    --standalone --onefile --plugin-enable=pylint-warnings --plugin-enable=pylint-warnings \
    -o main.so

mv main.so lib
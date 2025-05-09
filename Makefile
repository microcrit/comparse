clean:
	rm -rf lib
	rm -rf __init__.{build,dist,onefile-build}
	rm -rf {src/,src/test/,}__pycache__
	rm -rf .pytest_cache

build:
	nuitka src/__init__.py \
		--standalone --onefile --plugin-enable=pylint-warnings --plugin-enable=pylint-warnings \
		-o main.so

	mv main.so lib

pytest:
	pytest \
		-v -s \
		--tb=short --disable-warnings --maxfail=1 \
		src/test/*.py
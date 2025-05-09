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

test:
	bash -c "time pytest -v -s --tb=short --disable-warnings --maxfail=1 src/test/*.py" > pytest.log 2>&1

	echo "--- Comparse benchmarks ---" > bench.txt

	echo -n "Test on " >> bench.txt
	date >> bench.txt

	echo -n "Python version: " >> bench.txt
	python3 --version >> bench.txt

	echo -n "As of commit " >> bench.txt
	git rev-parse HEAD >> bench.txt
	echo -n "Git branch: " >> bench.txt
	git rev-parse --abbrev-ref HEAD >> bench.txt
	echo -n "Git status: " >> bench.txt
	git status --porcelain | wc -l >> bench.txt

	echo "Hashes" >> bench.txt

	for file in $(shell find src -name '*.py'); do \
		echo "$$(md5sum $$file | cut -d' ' -f1) $$file" >> bench.txt; \
	done

	grep -E '([0-9]+ (passed|failed|skipped|deselected))' pytest.log | tail -1 | \
		sed 's/^\([0-9]\+\) \([a-z]\+\) \([a-z]\+\) \([a-z]\+\) \([a-z]\+\)/\1 - \2 - \3 - \4 - \5/' >> bench.txt

	grep -E 'real|user|sys' pytest.log | tail -3 | sed 's/real/- real time:/; s/user/- user time:/; s/sys/- sys time:/' >> bench.txt

	git diff --stat >> bench.txt
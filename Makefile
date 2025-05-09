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

	echo "# Comparse benchmarks" > bench.md
	
	echo -n "Test on " >> bench.md
	date >> bench.md

	echo -n "Python version: " >> bench.md
	python3 --version >> bench.md

	echo -n "As of commit " >> bench.md
	git rev-parse HEAD >> bench.md
	echo -n "Git branch: " >> bench.md
	git rev-parse --abbrev-ref HEAD >> bench.md
	echo -n "Git status: " >> bench.md
	git status --porcelain | wc -l >> bench.md

	echo "Hashes" >> bench.md

	for file in $(shell find src -name '*.py'); do \
		echo "$$(md5sum $$file | cut -d' ' -f1) $$file" >> bench.md; \
	done

	grep -E '([0-9]+ (passed|failed|skipped|deselected))' pytest.log | tail -1 | \
		sed 's/^\([0-9]\+\) \([a-z]\+\) \([a-z]\+\) \([a-z]\+\) \([a-z]\+\)/\1 - \2 - \3 - \4 - \5/' >> bench.md

	grep -E 'real|user|sys' pytest.log | tail -3 | sed 's/real/- real time:/; s/user/- user time:/; s/sys/- sys time:/' >> bench.md

	git diff --stat >> bench.md
.POSIX:
.SUFFIXES:

.PHONY: default
default: build

venv:
	python3 -m venv venv
	./venv/bin/python3 -m pip install -r requirements-dev.txt

.PHONY: build
build: clean
	python3 -m pip install -q -r requirements.txt --platform manylinux2014_x86_64 --only-binary=:all: --target build/
	rm -fr build/*.dist-info/
	cp manage.py build/
	cp -r project build/
	cp -r digimontcg build/
	./venv/bin/shiv --compressed --site-packages build --root /var/lib/digimontcg -p "/usr/bin/env python3" -e manage:main -o digimontcg.pyz

.PHONY: package
package: build
	nfpm package -p deb -t digimontcg.deb

.PHONY: deploy
deploy: package
	scp digimontcg.deb derz@digimontcg.online:/tmp
	ssh -t derz@digimontcg.online sudo dpkg -i /tmp/digimontcg.deb

.PHONY: test
test: venv
	./venv/bin/python3 manage.py test

.PHONY: format
format: venv
	./venv/bin/black manage.py digimontcg/ project/

.PHONY: clean
clean:
	rm -fr *.deb *.pyz build/ static/

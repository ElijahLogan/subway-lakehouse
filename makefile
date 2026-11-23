lambda:             ## build build/lambda.zip for arm64 Lambda (python 3.12)
	rm -rf build/pkg && mkdir -p build/pkg
	pip3 install -r ingestion/requirements.txt --target build/pkg \
		--platform manylinux2014_aarch64 --python-version 3.12 --only-binary=:all: --quiet
	cp -r ingestion/mta_ingest build/pkg/
	find build/pkg -name '__pycache__' -prune -exec rm -rf {} +
	cd build/pkg && zip -qr ../layer.zip .
	@du -h build/layer.zip
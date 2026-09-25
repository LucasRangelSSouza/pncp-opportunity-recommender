.PHONY: check reproduce

check:
	python -m unittest discover -s tests -v

reproduce:
	python -m pncp_recommender evaluate-release --output artifacts/release-v1

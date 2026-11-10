# Run records

One JSON file per experiment, written by `mlh.registry.record`. Each one stores the hashes of the data, the code and the
contract, library versions, the git commit, parameters, results and how many times the contract's test split has been
evaluated.

- Never edit a record by hand; the guard denies it. To change a result, change the code or the contract and run again.
- Commit the records you report: they are the evidence behind every number.
- For exploration, write to a scratch folder: `MLH_RUNS_DIR=/tmp/runs make demo`.
- Check a record with `make gate RUN=runs/<record>.json`.

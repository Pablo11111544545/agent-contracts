# Dependency Injection & Testing Notes

## dependency_provider

If your app has many services, use `dependency_provider(contract)` to supply them based on `contract.services`.

Recommended behavior:

- Fail fast if a required service is missing (in tests/CI).
- Keep service objects stateless or explicitly scoped.

## Testing Tool Nodes

- Unit test nodes by calling `node.execute(NodeInputs(...))` with stub services.
- Keep external calls behind service interfaces so you can stub them.

## Safe State

- Do not put secrets (API keys, tokens) into state slices.
- Prefer passing secrets via service instances, not state.

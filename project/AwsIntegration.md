# AWS integration test selection

Normal `Test` tasks (including `sbt check`) always exclude the ScalaTest tag
`edu.uic.cs441.scholarchain.storage.AwsIntegration`, even when AWS environment
variables are set. Tag individual live tests with that exact tag. The
`AwsIntegrationExclusionSentinelSpec` in build verification deliberately fails
if selected, so default tests verify exclusion without any AWS calls.

The storage `awsIntegration` configuration compiles the same test sources in a
separate configuration and selects only this tag. Its test loader and public
`test`, `testOnly` and `testQuick` entry points refuse execution unless both
`SCHOLARCHAIN_AWS_ITEST=1` and a nonblank `AWS_PROFILE` are explicitly supplied.
It does not use the SDK's implicit default profile as permission.

For a future approved Phase 14C run (not executed in Phase 7A):

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
SCHOLARCHAIN_AWS_ITEST=1 AWS_PROFILE=<approved-profile> sbt 'storage / AwsIntegration / test'
```

The profile/environment switches are necessary test-selection gates, not
authorization to mutate AWS. The Phase 14C human gate, concrete suite cleanup
procedure and cost bound remain required. The live suite is later-subphase
work. Never run build verification's tagged failure sentinel as a live suite.

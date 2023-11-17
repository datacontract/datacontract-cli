package datacontract

import "os/exec"

// allow mocking command execution
var cmdCombinedOutput = (*exec.Cmd).CombinedOutput

package main

import (
	"encoding/base64"
	"fmt"
	"os"
	"os/user"
	"strings"
)

type EnvServiceInterface interface {
	AddVariable(keyValue string)
	IsCurrentUserRoot() bool
	GetVariables() []string
}

type EnvService struct {
	Variables []string
}

func (f EnvService) GetVariables() []string {
	return f.Variables
}

func NewEnvService() *EnvService {
	variables := make([]string, 0)
	for _, value := range os.Environ() {
		variables = append(variables, value)
	}
	return &EnvService{
		Variables: variables,
	}
}

func (f *EnvService) AddVariable(keyValue string){
	f.Variables = append(f.Variables, keyValue)
}

func (f EnvService) IsCurrentUserRoot() bool {
	currentUser, err := user.Current()
	if err != nil {
		panic(err)
	}
	if currentUser.Username == "root" {
		return true
	}
	return false
}

// Writes environment variables that will be preserved into a docker container to a file (envFilePath).
// Format is: ENV_VAR_NAME="env var value".
// Blacklisted variables are respected. If any env variable is blacklisted, it will be saved with "DOJO_" prefix.
// If env var with "DOJO_" prefix already exists, its value is taken, instead of
// the primary variable. E.g. PWD is blacklisted, so it will be saved as "DOJO_PWD=/some/path".
// If DOJO_PWD already exists, it is preserved as is and we do nothing to preserve PWD value.
// Variables can be also blacklisted with asterisk, e.g. BASH*. This means that
// any variable starting with BASH will be blacklisted (and prefixed).
// Variables with DOJO_ prefix cannot be blacklisted.
func saveEnvToFile(fileService FileServiceInterface, envFilePath string, envFilePathMultiLine string,
		blacklistedVars string, currentVariables []string)  {
	if fileService == nil {
		panic("fileService was nil")
	}
	filteredEnvVariables := filterBlacklistedVariables(blacklistedVars, currentVariables)

	fileService.RemoveFile(envFilePath, true)
	singleLineVariablesStr := singleLineVariablesToString(filteredEnvVariables)
	fileService.WriteToFile(envFilePath, singleLineVariablesStr, "debug")

	fileService.RemoveFile(envFilePathMultiLine, true)
	multiLineVariablesStr := multiLineVariablesToString(filteredEnvVariables)
	fileService.WriteToFile(envFilePathMultiLine, multiLineVariablesStr, "debug")
}

type EnvironmentVariable struct {
	Key string
	Value string
	MultiLine bool
}
func (e EnvironmentVariable) String() string {
	return fmt.Sprintf("%s=%s", e.Key, e.Value)
}

func (e EnvironmentVariable) encryptValue() string {
	data := []byte(e.Value)
	str := base64.StdEncoding.EncodeToString(data)
	return str
}

// allVariables is a []string, where each element is of format: VariableName=VariableValue
func filterBlacklistedVariables(blacklistedVarsNames string, allVariables []string) []EnvironmentVariable {
	blacklistedVarsArr := strings.Split(blacklistedVarsNames, ",")
	envVariables := make([]EnvironmentVariable, 0)
	for _,v := range allVariables {
		arr := strings.SplitN(v,"=", 2)
		key := arr[0]
		value := arr[1]
		isMultiLine := (len(strings.Split(value, "\n")) > 1)
		var envVar EnvironmentVariable
		if key == "DISPLAY" {
			// this is highly opinionated
			envVar = EnvironmentVariable{"DISPLAY", "unix:0.0", isMultiLine}
		} else if existsVariableWithDOJOPrefix(key, allVariables) {
			// ignore this key, we will deal with DOJO_${key}
			continue
		} else if strings.HasPrefix(key, "DOJO_") {
			envVar = EnvironmentVariable{key, value, isMultiLine}
		} else if isVariableBlacklisted(key, blacklistedVarsArr) {
			envVar = EnvironmentVariable{fmt.Sprintf("DOJO_%s", key), value, isMultiLine}
		} else {
			envVar = EnvironmentVariable{key, value, isMultiLine}
		}
		envVariables = append(envVariables, envVar)
	}
	return envVariables
}

func singleLineVariablesToString(variables []EnvironmentVariable) string {
	singleLineVariablesStr := ""
	for _, e := range variables {
		if !e.MultiLine {
			singleLineVariablesStr += e.String()
			singleLineVariablesStr += "\n"
		}
	}
	return singleLineVariablesStr
}

// This function constructs such a string for each environment variable,
// so that when it is saved to a file and sourced (from bash),
// the variables values are decoded with base64.
func multiLineVariablesToString(variables []EnvironmentVariable) string {
	multiLineVariablesStr := ""
	for _, e := range variables {
		if e.MultiLine {
			multiLineVariablesStr += fmt.Sprintf("export %s=$(echo %s | base64 -d)\n", e.Key, e.encryptValue())
		}
	}
	return multiLineVariablesStr
}

func getEnvFilePaths(runID string, test string) (string,string) {
	if test == "true" {
		return fmt.Sprintf("/tmp/test-dojo-environment-%s", runID),
			fmt.Sprintf("/tmp/test-dojo-environment-multiline-%s", runID)
	} else {
		return fmt.Sprintf("/tmp/dojo-environment-%s", runID),
			fmt.Sprintf("/tmp/dojo-environment-multiline-%s", runID)
	}
}

func isVariableBlacklisted(variableName string, blacklistedVariables []string) bool {
	for _,v := range blacklistedVariables {
		if strings.HasSuffix(v, "*") {
			vNoSuffix := strings.TrimSuffix(v, "*")
			if strings.HasPrefix(variableName, vNoSuffix) {
				return true
			}
		}
		if variableName == v {
			return true
		}
	}
	return false
}

// true if e.g. USER and DOJO_USER are set
func existsVariableWithDOJOPrefix(variableName string, allVariables []string) bool {
	for _,v := range allVariables {
		arr := strings.SplitN(v,"=", 2)
		key := arr[0]

		if strings.HasPrefix(key, "DOJO_") {
			vNoPrefix := strings.TrimPrefix(key, "DOJO_")
			if vNoPrefix == variableName {
				return true
			}
		}
	}
	return false
}
#!/bin/sh

test_root=$(dirname $(perl -MCwd -M5.14.0 -e "say Cwd::realpath('$0')"))
wit_root=$(perl -MCwd -M5.14.0 -e "say Cwd::realpath('$test_root/..')")
wit_repo='git@github.com:sifive/wit'

export PATH=$wit_root:${PATH}

fail=0
pass=0

check() {
        check_name=$1
        shift;

        if $@
        then echo "PASS - ${check_name}"; ((pass++))
        else echo "FAIL - ${check_name}"; ((fail++))
        fi
}

report() {
        echo "PASS: $pass"
        echo "FAIL: $fail"
}

finish() {
        if [ $fail -eq 0 ]
        then echo "Test passed"; exit 0
        else echo "Test failed"; exit 1
        fi
}

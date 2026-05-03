#!/usr/bin/env bash

kubectl delete namespace bank --ignore-not-found
echo "Namespace 'bank' deleted."

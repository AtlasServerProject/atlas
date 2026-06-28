#!/bin/bash

echo "===================================="
echo " Atlas Environment Check"
echo "===================================="
echo

echo "Java:"
java -version | head -n 1

echo
echo "Servidor:"
systemctl is-active atlas

echo
echo "PostgreSQL:"
systemctl is-active postgresql
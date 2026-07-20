#!/usr/bin/env bash
cd "$(git rev-parse --show-toplevel)"

echo "What kind of release is it?"
echo "  1. patch - eg: 0.1.0 -> 0.1.1"
echo "  2. minor - eg: 0.1.1 -> 0.2.0"
echo "  3. major - eg: 0.2.1 -> 1.0.0"
echo "  4. prerelease - eg: 0.1.0 -> 0.1.1-alpha.0"

read -p "Select between 1 and 4 [default 1]: " RELEASE_TYPE
RELEASE_TYPE=${RELEASE_TYPE:-1}

case $RELEASE_TYPE in
  1)
    poetry version patch
    ;;
  2)
    poetry version minor
    ;;
  3)
    poetry version major
    ;;
  4)
    poetry version prerelease
    ;;
  *)
    echo "Invalid option; must select between 1 and 4"
    exit 1
esac

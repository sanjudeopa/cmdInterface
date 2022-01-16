#!/bin/bash
# shellcheck: ignore

EAP_PROD_HOST="https://prod.eu.eap.arm.com"
EAP_UAT_HOST="https://eu-uat.eap.arm.com"
EAP_HOST=$EAP_PROD_HOST

EAP_CONFIG="${HOME}/.config/arm-eap"
REQ_FILE="${EAP_CONFIG}/req.out"
PEM_FILE="${EAP_CONFIG}/cert.pem"
KEY_FILE="${EAP_CONFIG}/cert.key"

usage()
{
cat << EOF
Usage:
$0 -h -p -u -m -r

Maintain EAP certificates.

OPTIONS:
   -h      Show this message
   -p      Target Prod Servers
   -u      Target UAT servers
   -m      Target both UAT and Prod servers
   -r      Revoke certificate instead of requesting one.
EOF
}

generateQueries()
{
QUIET=""\
"--silent "\
"--output $REQ_FILE "\
"--write-out %{http_code} "\
""

GET=""\
"-u ${USER} "\
"-X GET "\
"${EAP_HOST}/api/certificate?user=${USER} "\
""

POST=""\
"-u ${USER} "\
"-X POST "\
"${EAP_HOST}/api/certificate?user=${USER} "\
""

DELETE=""\
"-u ${USER} "\
"-X DELETE "\
"${EAP_HOST}/api/certificate?user=${USER} "\
""
}

execute()
{
#
# Optional: revoke certificate
#
if [[ "$ACTION" == "REVOKE" ]] ; then
    echo 'Revoking certificate'
    status_code=$(curl $QUIET $DELETE)
    if [[ "$status_code" -ne "200" ]] ; then
        echo 'Cannot revoke certificate.'
        echo 'Please check you have entered your password correctly, and you are targeting the correct environment'
        echo 'if problems persist please contact the eap team over slack on the #help-eap channel with the following commands:'
        echo curl $DELETE
        exit 1
    fi
    rm -f $PEM_FILE
    rm -f $KEY_FILE
    echo "Removed ${PEM_FILE}"
    echo "Removed ${KEY_FILE}"
    exit 0
fi

#
# Default: get existing or create new certificate
#
mkdir -p $EAP_CONFIG

echo 'Retrieving existing certificate'
status_code=$(curl $QUIET $GET)

if [[ "$status_code" -ne "200" ]] ; then

    echo 'Cannot retrieve existing certificate, creating a new one'
    echo 'Creating new certificate'
    status_code=$(curl $QUIET $POST)

    if [[ "$status_code" -ne "200" ]] ; then
        echo 'Cannot create new certificate.'
        echo 'Please check you have entered your password correctly, and you are targeting the correct environment'
        echo 'if problems persist please contact the eap team over slack on the #help-eap channel with the following commands:'
        echo curl $GET
        echo curl $POST
     exit 1
    fi

fi

JSON_PEM="import sys,json; print(json.load(sys.stdin)['data']['certificate']['certificate'])"
JSON_KEY="import sys,json; print(json.load(sys.stdin)['data']['certificate']['key'])"

cat $REQ_FILE | python -c "$JSON_PEM" > $PEM_FILE
cat $REQ_FILE | python -c "$JSON_KEY" > $KEY_FILE

chmod 600 $PEM_FILE $KEY_FILE
rm -f $REQ_FILE

echo "Installed ${PEM_FILE}"
echo "Installed ${KEY_FILE}"
}

no_args="true"

while getopts "hurpm" OPTION
do
     case $OPTION in
         h)
             usage
             exit 1
             ;;
         u)
             echo 'Using UAT server'
             EAP_HOST=$EAP_UAT_HOST
             generateQueries
             execute
             exit 1
             ;;
         p)
             echo 'Using PROD server'
             EAP_HOST=$EAP_PROD_HOST
             generateQueries
             execute
             exit 1
             ;;
         m)
             echo 'Using PROD server'
             EAP_HOST=$EAP_PROD_HOST
             PEM_FILE="${EAP_CONFIG}/on-prem_prod_cert.pem"
             KEY_FILE="${EAP_CONFIG}/on-prem_prod_cert.key"
             generateQueries
             execute
             echo 'Using UAT server'
             EAP_HOST=$EAP_UAT_HOST
             PEM_FILE="${EAP_CONFIG}/on-prem_uat_cert.pem"
             KEY_FILE="${EAP_CONFIG}/on-prem_uat_cert.key"
             generateQueries
             execute
             exit 1
             ;;
         r)
             ACTION="REVOKE"
             exit 1
             ;;
         *)
           echo 'Invalid option, please run script with -h flag to see available flags'
           exit 1
           ;;
     esac
     no_args="false"
done

[[ "$no_args" == "true" ]] && { usage; exit 1; }

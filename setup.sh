# below commands read env variables from dockerfile to create/update appropiate trunks in livekt cloud account
lk sip inbound create "$INBOUND_TRUNK_JSON"
lk sip dispatch create "$DISPATCH_RULE_JSON"

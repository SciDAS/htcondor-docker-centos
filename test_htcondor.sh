useradd -m -s /bin/bash dmr
su - dmr

cat > sleep.sh <<EOF
#!/bin/sh
echo "Sleeping for 20 seconds..."
sleep 20
echo "Done"
exit 0
EOF

cat > sleep.sub <<EOF
executable = sleep.sh
initialdir = run\$(Process)
log = sleep.log
output = sleep.out
queue 1
EOF

mkdir run0

condor_submit sleep.sub

condor_status

condor_q


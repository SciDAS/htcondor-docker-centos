# the condor_pool user is used by the Python API
su - condor_pool

cat > sleep.sh <<EOF
#!/bin/sh
echo "Sleeping for 20 seconds..."
#sleep 20
echo \`env\`
exit 0
EOF

# the below requirements line should ensure that the job is run on OSG
# requirements = GLIDEIN_ResourceName == "SU-OG-CE"
cat > sleep.sub <<EOF
universe = vanilla 
executable = sleep.sh
initialdir = run\$(Process)
requirements = GLIDEIN_ResourceName == "SU-OG-CE"
log = sleep.log
output = sleep.out
error = sleep.err 
+ProjectName = "Test"
queue 1
EOF

mkdir run0

condor_submit sleep.sub

condor_status

condor_q


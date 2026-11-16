# kubernetes v1.37.2 pkg/controller/deployment/util/deployment_util.go 발췌 — https://raw.githubusercontent.com/kubernetes/kubernetes/v1.37.2/pkg/controller/deployment/util/deployment_util.go
		newStatus.ObservedGeneration >= deployment.Generation
}

// DeploymentProgressing reports progress for a deployment. Progress is estimated by comparing the
// current with the new status of the deployment that the controller is observing. More specifically,
// when new pods are scaled up or become ready or available, or old pods are scaled down, then we
// consider the deployment is progressing.
func DeploymentProgressing(deployment *apps.Deployment, newStatus *apps.DeploymentStatus) bool {
	oldStatus := deployment.Status

	// Old replicas that need to be scaled down
	oldStatusOldReplicas := oldStatus.Replicas - oldStatus.UpdatedReplicas
	newStatusOldReplicas := newStatus.Replicas - newStatus.UpdatedReplicas

	return (newStatus.UpdatedReplicas > oldStatus.UpdatedReplicas) ||
		(newStatusOldReplicas < oldStatusOldReplicas) ||
		newStatus.ReadyReplicas > deployment.Status.ReadyReplicas ||
		newStatus.AvailableReplicas > deployment.Status.AvailableReplicas
}

// used for unit testing
var nowFn = time.Now

// DeploymentTimedOut considers a deployment to have timed out once its condition that reports progress
// is older than progressDeadlineSeconds or a Progressing condition with a TimedOutReason reason already
// exists.
func DeploymentTimedOut(ctx context.Context, deployment *apps.Deployment, newStatus *apps.DeploymentStatus) bool {
	if !HasProgressDeadline(deployment) {
		return false
	}

	// Look for the Progressing condition. If it doesn't exist, we have no base to estimate progress.
	// If it's already set with a TimedOutReason reason, we have already timed out, no need to check
	// again.
	condition := GetDeploymentCondition(*newStatus, apps.DeploymentProgressing)
	if condition == nil {
		return false
	}
	// If the previous condition has been a successful rollout then we shouldn't try to
	// estimate any progress. Scenario:
	//
	// * progressDeadlineSeconds is smaller than the difference between now and the time
	//   the last rollout finished in the past.
	// * the creation of a new ReplicaSet triggers a resync of the Deployment prior to the
	//   cached copy of the Deployment getting updated with the status.condition that indicates
	//   the creation of the new ReplicaSet.
	//
	// The Deployment will be resynced and eventually its Progressing condition will catch
	// up with the state of the world.
	if condition.Reason == NewRSAvailableReason {
		return false
	}
	if condition.Reason == TimedOutReason {
		return true
	}
	logger := klog.FromContext(ctx)
	// Look at the difference in seconds between now and the last time we reported any
	// progress or tried to create a replica set, or resumed a paused deployment and
	// compare against progressDeadlineSeconds.
	from := condition.LastUpdateTime
	now := nowFn()
	delta := time.Duration(*deployment.Spec.ProgressDeadlineSeconds) * time.Second
	timedOut := from.Add(delta).Before(now)

	logger.V(4).Info("Deployment timed out from last progress check", "deployment", klog.KObj(deployment), "timeout", timedOut, "from", from, "now", now)
	return timedOut
}

// NewRSNewReplicas calculates the number of replicas a deployment's new RS should have.
// When one of the followings is true, we're rolling out the deployment; otherwise, we're scaling it.
// 1) The new RS is saturated: newRS's replicas == deployment's replicas
// 2) Max number of pods allowed is reached: deployment's replicas + maxSurge == all RSs' replicas
func NewRSNewReplicas(deployment *apps.Deployment, allRSs []*apps.ReplicaSet, newRS *apps.ReplicaSet) (int32, error) {
	switch deployment.Spec.Strategy.Type {
	case apps.RollingUpdateDeploymentStrategyType:
		// Check if we can scale up.

## pkg/features/kube_features.go (DeploymentReplicaSetTerminatingReplicas)
	DefaultPodSysctls featuregate.Feature = "DefaultPodSysctls"

	// owner: @atiratree
	// kep: http://kep.k8s.io/3973
	//
	// Deployments and replica sets can now also track terminating pods via .status.terminatingReplicas.
	DeploymentReplicaSetTerminatingReplicas featuregate.Feature = "DeploymentReplicaSetTerminatingReplicas"
	DeploymentReplicaSetTerminatingReplicas: {
		{Version: version.MustParse("1.33"), Default: false, PreRelease: featuregate.Alpha},
		{Version: version.MustParse("1.35"), Default: true, PreRelease: featuregate.Beta},
	},

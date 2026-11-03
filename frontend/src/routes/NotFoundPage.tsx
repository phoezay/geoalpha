import { Button, EmptyState } from '../components/ui'

export function NotFound() {
  return (
    <EmptyState
      title="Page not found"
      description="The page you are looking for does not exist."
      action={
        <Button variant="primary" onClick={() => window.location.assign('/')}>
          Start an analysis
        </Button>
      }
    />
  )
}

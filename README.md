# Quy trình quản lý mã nguồn (Branching & Workflow)

Mục tiêu: đảm bảo phát triển song song an toàn, dễ code review, có CI/CD, và release ổn định.

## Tổng quan branchmark
- `main`  
  - Luôn ở trạng thái deploy được lên production. Chỉ merge PR đã qua review và CI passing. Mỗi commit trên `main` là một release (gắn tag).
- Feature branches: `feature/<ISSUE>-short-description`  
  - Dùng để phát triển tính năng/issue. Xuất phát từ `develop` hoặc `main` (tùy chiến lược).
- Chore/ci/refactor: `chore/...`, `ci/...`, `refactor/...`  
  - Công việc không thêm feature (cấu hình, nâng phụ thuộc, refactor).

## Quy tắc đặt tên
- Lowercase, dấu `-` ngăn cách.
- Bắt đầu bằng loại branch: `feature/`, `chore/`.
- Kèm ID issue khi có: `feature/123-login-form`.

## Commit message (gợi ý: Conventional Commits)
- format: `<type>(<scope>): <short summary>`
- type: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`
- Ví dụ: `feat(auth): add JWT refresh token`, `fix(api): handle null response`

## Pull Request (PR)
- Branch đích: `main`.
- Tiêu chí mở PR:
  - Có mô tả ngắn: mục tiêu, cách kiểm thử, ảnh chụp màn hình nếu cần.
  - Chạy local tests & CI passing.
  - Kèm link issue/task.
- Review:
  - Ít nhất 1 reviewer (2 cho thay đổi lớn).
  - Reviewer kiểm tra logic, bảo mật, performance, style.
- Merge strategy:
  - Dùng "Squash and merge" để giữ lịch sử gọn gàng (hoặc "Merge commit" nếu muốn giữ commit history đầy đủ).
  - Không dùng fast-forward cho release/hotfix nếu cần giữ branch history.

## CI/CD
- Mỗi PR phải trigger pipeline:
  - Build, lint, unit tests.
  - Nếu là PR vào `main`/`release`, thêm integration tests và deploy preview.
- Branch protection:
  - Bắt buộc PR reviews.
  - Bắt buộc CI passing trước khi merge.
  - Không cho phép force push vào `main`.

## Ví dụ lệnh Git thường dùng
- Tạo feature branch:
  - git checkout -b feature/123-login-form develop
- Push và mở PR:
  - git push -u origin feature/123-login-form
- Hotfix:
  - git checkout -b hotfix/critical-500 main
  - ...fix...
  - git push origin hotfix/critical-500

## Best practices ngắn gọn
- Giữ branch nhỏ, tập trung vào 1 việc.
- Viết commit rõ ràng, kèm issue ID.
- Luôn chạy test & lint trước khi mở PR.
- Documentation cập nhật cùng code (README, CHANGELOG).
- Sử dụng tags semantic versioning (vMAJOR.MINOR.PATCH).


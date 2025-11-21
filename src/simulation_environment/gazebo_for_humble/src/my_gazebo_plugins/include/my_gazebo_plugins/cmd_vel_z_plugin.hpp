
#ifndef CMD_VEL_Z_PLUGIN_HPP
#define CMD_VEL_Z_PLUGIN_HPP

#include <gazebo/gazebo.hh>
#include <gazebo/physics/Model.hh>
#include <gazebo/physics/Link.hh>
#include <gazebo/common/Events.hh>
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>

namespace gazebo
{
    class GazeboRosPlanarMovePrivate;

    /// Simple model controller that uses a twist message to move an entity on the xy plane.
    /*
     * \author  Piyush Khandelwal (piyushk@gmail.com)
     *
     * \date  29 July 2013
     */

    /**
      Example Usage:
      \code{.xml}
        <plugin name="gazebo_ros_planar_move" filename="libgazebo_ros_planar_move.so">

          <ros>

            <!-- Add a namespace -->
            <namespace>/demo</namespace>

            <!-- Remap the default topic -->
            <remapping>cmd_vel:=custom_cmd_vel</remapping>
            <remapping>odom:=custom_odom</remapping>

          </ros>

          <update_rate>100</update_rate>
          <publish_rate>10</publish_rate>

          <!-- output -->
          <publish_odom>true</publish_odom>
          <publish_odom_tf>true</publish_odom_tf>

          <odometry_frame>odom_demo</odometry_frame>
          <robot_base_frame>link</robot_base_frame>

          <covariance_x>0.0001</covariance_x>
          <covariance_y>0.0001</covariance_y>
          <covariance_yaw>0.01</covariance_yaw>

        </plugin>
      \endcode
    */

    class GazeboRosPlanarMove : public gazebo::ModelPlugin
    {
    public:
        /// Constructor
        GazeboRosPlanarMove();

        /// Destructor
        ~GazeboRosPlanarMove();

    protected:
        // Documentation inherited
        void Load(gazebo::physics::ModelPtr model, sdf::ElementPtr sdf) override;

        // Documentation inherited
        void Reset() override;

    private:
        /// Private data pointer
        std::unique_ptr<GazeboRosPlanarMovePrivate> impl_;
    };
} // namespace gazebo_plugins

#endif // GAZEBO_PLUGINS__GAZEBO_ROS_PLANAR_MOVE_HPP_